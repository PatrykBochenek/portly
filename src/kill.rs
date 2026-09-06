use crate::model::KillError;
use crate::ports::wait_for_port_free;
use crate::probe;

/// Kill the process(es) using `port` and verify it becomes free.
#[cfg(any(target_os = "linux", target_os = "macos", windows))]
pub fn kill_on_port(port: u16, force: bool) -> Result<bool, KillError> {
    // #50: kill must target TCP LISTEN sockets only. Matching "any socket with
    // this local port" would also SIGTERM unrelated UDP owners (ephemeral DNS
    // sockets, systemd-resolved) and TCP ESTABLISHED client sockets whose local
    // port happens to collide — TCP and UDP port spaces are independent.
    let processes = probe::find_processes(port, true);
    if processes.is_empty() {
        // The port is busy but no matching process was found (for example
        // it is owned by another user and hidden from us). We cannot kill.
        return Ok(false);
    }
    let mut denied = false;
    let mut killed_any = false;
    for process in &processes {
        match crate::platform::kill_pid(process.pid, force) {
            Ok(()) => killed_any = true,
            Err(KillError::Permission) => denied = true,
            Err(KillError::Other(_)) => {}
        }
    }
    if denied && !killed_any {
        return Err(KillError::Permission);
    }
    // Give the kernel a moment and verify the port actually freed up
    // instead of blindly reporting success.
    Ok(wait_for_port_free(port))
}

#[cfg(not(any(target_os = "linux", target_os = "macos", windows)))]
pub fn kill_on_port(port: u16, force: bool) -> Result<bool, KillError> {
    crate::platform::kill_on_port(port, force)
}

#[cfg(test)]
#[cfg(any(target_os = "linux", target_os = "macos", windows))]
mod tests {
    use super::kill_on_port;

    #[test]
    fn kill_on_port_free_port_returns_false() {
        // No process owns a fresh port, so there is nothing to kill and the
        // port is not "freed" by us — the function must report Ok(false).
        let port = std::net::TcpListener::bind("127.0.0.1:0")
            .unwrap()
            .local_addr()
            .unwrap()
            .port();
        assert!(!kill_on_port(port, false).unwrap());
    }

    #[test]
    fn kill_on_port_does_not_target_udp_owner() {
        // #50: kill must not SIGTERM a process whose UDP socket happens to
        // share the port with an unrelated TCP listener. A UDP-only port has
        // no LISTEN owner, so kill reports nothing-to-kill.
        let udp = std::net::UdpSocket::bind("127.0.0.1:0").unwrap();
        let port = udp.local_addr().unwrap().port();
        assert!(!kill_on_port(port, false).unwrap());
    }
}
