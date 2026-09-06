use crate::model::KillError;
use crate::ports::wait_for_port_free;
use crate::probe;

/// True when `pid` is the current process — killing it would terminate the
/// caller (issue #49). Port-cleanup libraries are typically called from the
/// very process they are cleaning up after.
fn is_self_pid(pid: u32) -> bool {
    pid == std::process::id()
}

/// Kill the process(es) using `port` and verify it becomes free.
#[cfg(any(target_os = "linux", target_os = "macos", windows))]
pub fn kill_on_port(port: u16, force: bool) -> Result<bool, KillError> {
    let processes = probe::find_processes(port, false);
    if processes.is_empty() {
        // The port is busy but no matching process was found (for example
        // it is owned by another user and hidden from us). We cannot kill.
        return Ok(false);
    }
    let mut denied = false;
    let mut killed_any = false;
    for process in &processes {
        // #49: never terminate our own process. In-process test servers are
        // the primary use case for a port-cleanup library; killing self would
        // SIGTERM/SIGKILL the Python process mid-call on every platform.
        if is_self_pid(process.pid) {
            continue;
        }
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
    use super::{is_self_pid, kill_on_port};

    #[test]
    fn is_self_pid_matches_current_process() {
        assert!(is_self_pid(std::process::id()));
        assert!(!is_self_pid(0));
        assert!(!is_self_pid(u32::MAX));
    }

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
}
