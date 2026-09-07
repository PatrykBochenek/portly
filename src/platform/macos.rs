use crate::model::{KillError, PortProcess};
use libproc::libproc::bsd_info::BSDInfo;
use libproc::libproc::file_info::{pidfdinfo, ListFDs, ProcFDType};
use libproc::libproc::net_info::{SocketFDInfo, SocketInfoKind, TcpSIState};
use libproc::libproc::proc_pid::{listpidinfo, name, pidinfo, pidpath};
use libproc::processes::{pids_by_type, ProcFilter};
use std::collections::HashSet;

pub fn find_processes(port: u16, listen_only: bool) -> Vec<PortProcess> {
    let mut out = Vec::new();
    let mut seen: HashSet<i32> = HashSet::new();

    let Ok(procs) = pids_by_type(ProcFilter::All) else {
        return out;
    };

    'next: for p in procs {
        let pid = p as i32;
        if seen.contains(&pid) {
            continue;
        }
        // Size the fd list from the process's actual fd count with a
        // little headroom (a fixed cap silently misses sockets in
        // fd-heavy processes); fall back to a generous default.
        let mut max_fds = pidinfo::<BSDInfo>(pid, 0)
            .map(|info| info.pbi_nfiles as usize + 32)
            .unwrap_or(4096);
        // #61: a process can open fds between the pidinfo count and the
        // listpidinfo call, making the buffer too small and silently missing
        // sockets. Grow the buffer and retry a bounded number of times before
        // giving up (EPERM for other users' processes stays a miss).
        let fds = loop {
            match listpidinfo::<ListFDs>(pid, max_fds) {
                Ok(fds) => break fds,
                Err(_) if max_fds < 1 << 20 => {
                    max_fds = max_fds.saturating_mul(2);
                }
                Err(_) => continue 'next,
            }
        };
        for fd in &fds {
            if !matches!(ProcFDType::from(fd.proc_fdtype), ProcFDType::Socket) {
                continue;
            }
            let Ok(socket) = pidfdinfo::<SocketFDInfo>(pid, fd.proc_fd) else {
                continue;
            };
            let kind = SocketInfoKind::from(socket.psi.soi_kind);
            let (local_port, is_listening) = match kind {
                SocketInfoKind::In => unsafe {
                    (socket.psi.soi_proto.pri_in.insi_lport as u16, false)
                },
                SocketInfoKind::Tcp => unsafe {
                    let state = TcpSIState::from(socket.psi.soi_proto.pri_tcp.tcpsi_state);
                    (
                        socket.psi.soi_proto.pri_tcp.tcpsi_ini.insi_lport as u16,
                        matches!(state, TcpSIState::Listen),
                    )
                },
                _ => continue,
            };
            if u16::from_be(local_port) != port {
                continue;
            }
            if listen_only && !is_listening {
                continue;
            }
            // The process can exit between socket enumeration and the
            // name lookup; a vanished process must not fail the scan.
            let Ok(process_name) = name(pid) else {
                continue 'next;
            };
            seen.insert(pid);
            out.push(PortProcess {
                pid: pid as u32,
                name: process_name,
                cmd: pidpath(pid).unwrap_or_default(),
            });
            continue 'next;
        }
    }
    out
}

pub fn kill_pid(pid: u32, force: bool) -> Result<(), KillError> {
    use nix::errno::Errno;
    use nix::sys::signal::{kill, Signal};
    use nix::unistd::Pid;

    if pid == std::process::id() {
        return Err(KillError::Other(
            "refusing to kill the calling process".into(),
        ));
    }
    if pid <= 1 {
        return Err(KillError::Other(
            "refusing to kill init/system process".into(),
        ));
    }

    let signal = if force {
        Signal::SIGKILL
    } else {
        Signal::SIGTERM
    };
    match kill(Pid::from_raw(pid as i32), signal) {
        Ok(()) => Ok(()),
        Err(Errno::ESRCH) => Ok(()), // process already gone
        Err(Errno::EPERM) => Err(KillError::Permission),
        Err(e) => Err(KillError::Other(e.to_string())),
    }
}
