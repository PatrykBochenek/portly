/// Check if a port is available on localhost.
pub fn is_port_free(port: u16) -> bool {
    port_check::is_local_port_free(port)
}

/// Find a free port on localhost, optionally preferring a specific port.
pub fn find_free_port(preferred: Option<u16>) -> Option<u16> {
    if let Some(p) = preferred {
        if p != 0 && port_check::is_local_port_free(p) {
            return Some(p);
        }
    }
    port_check::free_local_port()
}

/// Find `count` distinct free ports within `[lo, hi]` (inclusive), scanning
/// upward from `lo`. Returns fewer than `count` (possibly empty) if the range
/// is exhausted — the caller decides whether that is an error.
pub fn find_free_ports_in_range(lo: u16, hi: u16, count: usize) -> Vec<u16> {
    let mut found = Vec::new();
    if lo == 0 || lo > hi || count == 0 {
        return found;
    }

    let mut cursor = lo;
    loop {
        // Port 0 is never a usable free port; skip it if it appears.
        if cursor != 0 && port_check::is_local_port_free(cursor) {
            found.push(cursor);
            if found.len() == count {
                break;
            }
        }
        if cursor == hi {
            break;
        }
        cursor += 1;
    }
    found
}

/// Wait up to ~1s for the port to become free, polling every 50ms.
///
/// Returns `true` once the port is actually free, so callers report the
/// truth instead of blindly claiming success.
pub fn wait_for_port_free(port: u16) -> bool {
    use std::time::{Duration, Instant};

    let deadline = Instant::now() + Duration::from_secs(1);
    while Instant::now() < deadline {
        if port_check::is_local_port_free(port) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(50));
    }
    false
}

#[cfg(test)]
mod tests {
    use super::{find_free_port, find_free_ports_in_range, is_port_free, wait_for_port_free};
    use std::net::TcpListener;

    /// Bind a listener, grab its port, then drop it so the port is free.
    fn free_port() -> u16 {
        TcpListener::bind("127.0.0.1:0")
            .unwrap()
            .local_addr()
            .unwrap()
            .port()
    }

    #[test]
    fn is_port_free_reflects_bound_state() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        assert!(!is_port_free(port), "bound port must not be free");
        drop(listener);
        assert!(is_port_free(port), "port must be free after close");
    }

    #[test]
    fn find_free_port_without_preference_returns_free_port() {
        let port = find_free_port(None).expect("a free port must exist");
        assert_ne!(port, 0);
        assert!(is_port_free(port));
    }

    #[test]
    fn find_free_port_treats_zero_preference_as_none() {
        let port = find_free_port(Some(0)).expect("a free port must exist");
        assert_ne!(port, 0);
        assert!(is_port_free(port));
    }

    #[test]
    fn find_free_port_returns_free_preferred_port() {
        // Tests run in parallel, so another test can grab the port between
        // our free-port probe and the call; retry a few times.
        for _ in 0..10 {
            let preferred = free_port();
            if find_free_port(Some(preferred)) == Some(preferred) {
                return;
            }
        }
        panic!("preferred free port was never honored (contended by parallel tests?)");
    }

    #[test]
    fn find_free_port_skips_occupied_preferred_port() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let occupied = listener.local_addr().unwrap().port();
        let port = find_free_port(Some(occupied)).expect("a free port must exist");
        assert_ne!(port, occupied);
        assert!(is_port_free(port));
    }

    #[test]
    fn find_free_ports_in_range_rejects_invalid_input() {
        assert!(
            find_free_ports_in_range(0, 100, 1).is_empty(),
            "lo == 0 is invalid"
        );
        assert!(
            find_free_ports_in_range(100, 50, 1).is_empty(),
            "lo > hi is invalid"
        );
        assert!(
            find_free_ports_in_range(1024, 65535, 0).is_empty(),
            "count == 0 is invalid"
        );
    }

    #[test]
    fn find_free_ports_in_range_returns_count_distinct_free_ports() {
        let ports = find_free_ports_in_range(20000, 60000, 3);
        assert_eq!(ports.len(), 3, "expected three free ports in a wide range");
        let mut sorted = ports.clone();
        sorted.sort_unstable();
        sorted.dedup();
        assert_eq!(sorted.len(), 3, "ports must be distinct");
        for port in &ports {
            assert!((20000..=60000).contains(port), "{port} outside range");
            assert!(is_port_free(*port), "{port} must be free");
        }
    }

    #[test]
    fn find_free_ports_in_range_returns_fewer_when_range_exhausted() {
        // A single-port range can never yield two free ports, regardless of
        // whether that one port is free (privileged ports are typically not
        // bindable by unprivileged users anyway).
        let ports = find_free_ports_in_range(1, 1, 5);
        assert!(ports.len() < 2, "single-port range cannot yield two ports");
    }

    #[test]
    fn find_free_ports_in_range_handles_upper_boundary_without_overflow() {
        // cursor == hi must break before incrementing past u16::MAX.
        let ports = find_free_ports_in_range(65535, 65535, 1);
        assert!(ports.len() <= 1);
        for port in &ports {
            assert!(is_port_free(*port));
        }
    }

    #[test]
    fn wait_for_port_free_returns_false_while_bound() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        assert!(!wait_for_port_free(port), "bound port must not report free");
    }

    #[test]
    fn wait_for_port_free_returns_true_after_close() {
        let port = free_port();
        assert!(wait_for_port_free(port), "freed port must report free");
    }
}
