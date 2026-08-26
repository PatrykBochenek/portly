use crate::model::{KillError, PortProcess};
use procfs::process::FDTarget;
use std::collections::HashSet;

/// Collect the `/proc` socket inodes for `port`.
///
/// When `listen_only` is true, only TCP sockets in the LISTEN state
/// are considered (used by `get_info`); otherwise TCP and UDP sockets
/// in any state are included (used by `kill`).
fn socket_inodes(port: u16, listen_only: bool) -> HashSet<u64> {
    let mut inodes = HashSet::new();

    for entries in [procfs::net::tcp(), procfs::net::tcp6()]
        .into_iter()
        .flatten()
    {
        for entry in entries {
            if entry.local_address.port() == port
                && (!listen_only || entry.state == procfs::net::TcpState::Listen)
            {
                inodes.insert(entry.inode);
            }
        }
    }

    if !listen_only {
        for entries in [procfs::net::udp(), procfs::net::udp6()]
            .into_iter()
            .flatten()
        {
            for entry in entries {
                if entry.local_address.port() == port {
                    inodes.insert(entry.inode);
                }
            }
        }
    }

    inodes
}

/// Map socket inodes to their owning processes in a single pass over
/// `/proc/<pid>/fd`.
fn processes_for_inodes(inodes: &HashSet<u64>) -> Vec<PortProcess> {
    let mut out = Vec::new();
    if inodes.is_empty() {
        return out;
    }

    let Ok(processes) = procfs::process::all_processes() else {
        return out;
    };

    'next: for process in processes.flatten() {
        let Ok(fds) = process.fd() else { continue };

        for fd in fds.flatten() {
            if let FDTarget::Socket(inode) = fd.target {
                if inodes.contains(&inode) {
                    out.push(PortProcess {
                        pid: process.pid() as u32,
                        name: process.stat().map(|s| s.comm).unwrap_or_default(),
                        cmd: process
                            .cmdline()
                            .ok()
                            .map(|parts| parts.join(" "))
                            .unwrap_or_default(),
                    });
                    // One entry per process, even when several fds match.
                    continue 'next;
                }
            }
        }
    }
    out
}

pub fn find_processes(port: u16, listen_only: bool) -> Vec<PortProcess> {
    processes_for_inodes(&socket_inodes(port, listen_only))
}

pub fn kill_pid(pid: u32, force: bool) -> Result<(), KillError> {
    use nix::errno::Errno;
    use nix::sys::signal::{kill, Signal};
    use nix::unistd::Pid;

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

#[cfg(test)]
mod tests {
    use super::{kill_pid, processes_for_inodes, socket_inodes};
    use std::net::{TcpListener, UdpSocket};

    #[test]
    fn socket_inodes_finds_listening_tcp_socket() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        assert_eq!(
            socket_inodes(port, true).len(),
            1,
            "LISTEN socket must match"
        );
        assert_eq!(socket_inodes(port, false).len(), 1);
    }

    #[test]
    fn socket_inodes_finds_udp_only_when_not_listen_only() {
        let sock = UdpSocket::bind("127.0.0.1:0").unwrap();
        let port = sock.local_addr().unwrap().port();
        assert!(
            socket_inodes(port, true).is_empty(),
            "UDP must be ignored in listen-only mode"
        );
        assert_eq!(
            socket_inodes(port, false).len(),
            1,
            "UDP must match when not listen-only"
        );
    }

    #[test]
    fn socket_inodes_empty_for_fresh_port() {
        let port = TcpListener::bind("127.0.0.1:0")
            .unwrap()
            .local_addr()
            .unwrap()
            .port();
        assert!(socket_inodes(port, true).is_empty());
        assert!(socket_inodes(port, false).is_empty());
    }

    #[test]
    fn processes_for_inodes_maps_inode_to_current_process() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let inodes = socket_inodes(port, false);
        let processes = processes_for_inodes(&inodes);
        assert_eq!(processes.len(), 1, "expected one owning process");
        assert_eq!(processes[0].pid, std::process::id());
        assert!(!processes[0].name.is_empty());
    }

    #[test]
    fn processes_for_inodes_empty_for_empty_inode_set() {
        assert!(processes_for_inodes(&Default::default()).is_empty());
    }

    #[test]
    fn kill_pid_missing_process_is_ok() {
        // Spawn and reap a child so its pid is guaranteed gone: kill(2) then
        // returns ESRCH, which the probe maps to Ok (process already gone).
        let mut child = std::process::Command::new("true").spawn().unwrap();
        let pid = child.id();
        let status = child.wait().unwrap();
        assert!(status.success());
        assert_eq!(kill_pid(pid, false).unwrap(), ());
        assert_eq!(kill_pid(pid, true).unwrap(), ());
    }
}
