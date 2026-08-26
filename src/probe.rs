use crate::model::PortProcess;
use crate::platform;

/// Find processes using `port`.
///
/// When `listen_only` is true, only listening sockets are considered (used by
/// `get_info`); otherwise TCP and UDP sockets in any state are included (used
/// by `kill`).
pub fn find_processes(port: u16, listen_only: bool) -> Vec<PortProcess> {
    platform::find_processes(port, listen_only)
}

#[cfg(test)]
#[cfg(any(target_os = "linux", target_os = "macos", windows))]
mod tests {
    use std::net::TcpListener;

    use crate::probe::find_processes;

    #[test]
    fn finds_listener_in_current_process() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let processes = find_processes(port, true);
        assert_eq!(
            processes.len(),
            1,
            "expected exactly one process on the port"
        );
        assert_eq!(processes[0].pid, std::process::id());
        assert!(!processes[0].name.is_empty());
    }

    #[test]
    fn fresh_port_has_no_processes() {
        // Ephemeral ports can be grabbed by parallel tests between bind and
        // probe; retry with a fresh port on collision.
        for _ in 0..10 {
            let port = TcpListener::bind("127.0.0.1:0")
                .unwrap()
                .local_addr()
                .unwrap()
                .port();
            let processes = find_processes(port, true);
            if processes.is_empty() {
                return;
            }
        }
        panic!("repeatedly failed to observe a process-free port");
    }

    #[test]
    fn finds_ipv6_listener_in_current_process() {
        let listener = TcpListener::bind("[::1]:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let processes = find_processes(port, true);
        assert_eq!(processes.len(), 1, "expected one process on the IPv6 port");
        assert_eq!(processes[0].pid, std::process::id());
    }

    #[test]
    fn finds_udp_socket_in_current_process() {
        use std::net::UdpSocket;

        let sock = UdpSocket::bind("127.0.0.1:0").unwrap();
        let port = sock.local_addr().unwrap().port();
        // UDP sockets are only attributed when not listen-only (see platform
        // probe docs: listen-only covers TCP LISTEN for get_info).
        let processes = find_processes(port, false);
        assert_eq!(processes.len(), 1, "expected one process on the UDP port");
        assert_eq!(processes[0].pid, std::process::id());
    }

    #[test]
    fn udp_socket_not_attributed_when_listen_only() {
        use std::net::UdpSocket;

        let sock = UdpSocket::bind("127.0.0.1:0").unwrap();
        let port = sock.local_addr().unwrap().port();
        let processes = find_processes(port, true);
        assert!(
            processes.is_empty(),
            "UDP must not be attributed in listen-only mode"
        );
    }

    #[test]
    fn listen_only_filters_established_sockets() {
        use std::net::TcpStream;

        // A connected client socket is ESTABLISHED, not LISTEN: it must show
        // up for kill (listen_only = false) but not for get_info (true).
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let server_port = listener.local_addr().unwrap().port();
        let client = TcpStream::connect(("127.0.0.1", server_port)).unwrap();
        let client_port = client.local_addr().unwrap().port();
        let _server_side = listener.accept().unwrap();

        let all = find_processes(client_port, false);
        assert_eq!(
            all.len(),
            1,
            "established socket must be found when not listen-only"
        );
        assert_eq!(all[0].pid, std::process::id());

        let listen_only = find_processes(client_port, true);
        assert!(
            listen_only.is_empty(),
            "established socket must be filtered out in listen-only mode"
        );
    }

    #[test]
    fn deduplicates_dual_stack_listeners_on_same_port() {
        // An IPv4 and an IPv6 listener bound to the *same* port in this
        // process must surface as exactly one process entry.
        let v4 = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = v4.local_addr().unwrap().port();
        let v6 = TcpListener::bind(format!("[::1]:{port}")).unwrap();
        assert_eq!(v6.local_addr().unwrap().port(), port);

        let processes = find_processes(port, true);
        assert_eq!(processes.len(), 1, "dual-stack listeners must deduplicate");
        assert_eq!(processes[0].pid, std::process::id());
    }

    #[test]
    fn finds_listener_when_process_has_many_fds() {
        // Regression: the socket-fd scan used to stop at the first 1024 fds.
        // Open >1024 sockets first so the listener under test gets a high fd
        // index, then confirm the probe still finds it.
        #[cfg(unix)]
        {
            let rlim = libc::rlimit {
                rlim_cur: 4096,
                rlim_max: 8192,
            };
            let _ = unsafe { libc::setrlimit(libc::RLIMIT_NOFILE, &rlim) };
        }

        let mut sockets = Vec::new();
        while sockets.len() < 1100 {
            match TcpListener::bind("127.0.0.1:0") {
                Ok(s) => sockets.push(s),
                Err(_) => break, // environment refused; still verify below
            }
        }

        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let processes = find_processes(port, true);
        assert_eq!(
            processes.len(),
            1,
            "expected one process on the high-fd port"
        );
        assert_eq!(processes[0].pid, std::process::id());
    }

    #[test]
    fn port_freed_after_close_has_no_processes() {
        // A listener that was bound and then closed must not appear as a
        // process owner once the socket is gone. Ephemeral ports can be
        // rebound by parallel tests after close; retry with a fresh port.
        for _ in 0..10 {
            let port;
            {
                let listener = TcpListener::bind("127.0.0.1:0").unwrap();
                port = listener.local_addr().unwrap().port();
                let processes_while_open = find_processes(port, true);
                assert_eq!(processes_while_open.len(), 1);
            }
            let processes_after_close = find_processes(port, true);
            if processes_after_close.is_empty() {
                return;
            }
        }
        panic!("repeatedly failed to observe a freed port");
    }
}
