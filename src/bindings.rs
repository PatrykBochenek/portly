use pyo3::prelude::*;
use pyo3::types::PyModule;
use pyo3::IntoPyObjectExt;
use std::collections::HashMap;

use crate::model::{KillError, PortProcess};
use crate::{kill as kill_mod, ports, probe};

/// Convert an infallible Rust value into a Python object.
fn to_pyobj<'py>(py: Python<'py>, value: impl IntoPyObject<'py>) -> Py<PyAny> {
    value.into_py_any(py).expect("conversion is infallible")
}

/// Build the public `{"pid", "name", "cmd"}` info dict for a process.
fn info_dict(py: Python<'_>, process: &PortProcess) -> HashMap<String, Py<PyAny>> {
    let mut info = HashMap::new();
    info.insert("pid".to_string(), to_pyobj(py, process.pid));
    info.insert("name".to_string(), to_pyobj(py, process.name.clone()));
    info.insert("cmd".to_string(), to_pyobj(py, process.cmd.clone()));
    info
}

// =============================================================================
// PORT AVAILABILITY
// =============================================================================

/// Check if a port is available on localhost.
///
/// Args:
///     port: Port number to check (1-65535)
///
/// Returns:
///     True if port is available, False if in use
///
/// Example:
///     >>> import portly
///     >>> portly.is_available(8000)
///     True
#[pyfunction]
fn is_available(port: u16) -> bool {
    if port == 0 {
        return false;
    }
    ports::is_port_free(port)
}

// =============================================================================
// FIND FREE PORT
// =============================================================================

/// Find a free port on localhost.
///
/// Args:
///     preferred: Optional preferred port number. If provided and free, returns it.
///                If occupied, returns a different free port.
///
/// Returns:
///     A free port number
///
/// Raises:
///     OSError: If no free port could be found
///
/// Note:
///     The returned port can be taken by another process between this check
///     and when you actually bind to it (TOCTOU). Prefer binding to port 0
///     and letting the OS pick if you need a race-free reservation.
///
/// Example:
///     >>> port = portly.find_free(8000)
///     >>> port = portly.find_free()  # Any free port
#[pyfunction]
#[pyo3(signature = (preferred=None))]
fn find_free(preferred: Option<u16>) -> PyResult<u16> {
    ports::find_free_port(preferred)
        .ok_or_else(|| pyo3::exceptions::PyOSError::new_err("Could not find a free port"))
}

// =============================================================================
// WAIT UNTIL FREE
// =============================================================================

/// Wait for a port to become free.
///
/// Args:
///     port: Port number to wait for
///     timeout: Maximum seconds to wait (default: 30)
///
/// Returns:
///     True if port became free, False if timeout reached
///
/// Example:
///     >>> portly.wait_until_free(5432, timeout=30)
///     True
#[pyfunction]
#[pyo3(signature = (port, timeout=30))]
fn wait_until_free(py: Python<'_>, port: u16, timeout: u64) -> bool {
    if port == 0 {
        return false;
    }
    // Release the GIL while polling so other Python threads can run
    // (e.g. the thread that will free the port we are waiting for).
    py.detach(move || {
        use std::time::{Duration, Instant};

        let timeout = Duration::from_secs(timeout);
        let started = Instant::now();
        loop {
            if ports::is_port_free(port) {
                return true;
            }

            let remaining = timeout.saturating_sub(started.elapsed());
            if remaining.is_zero() {
                return false;
            }
            std::thread::sleep(Duration::from_millis(100).min(remaining));
        }
    })
}

// =============================================================================
// WAIT FOR SERVER
// =============================================================================

/// Wait for a server to start accepting TCP connections on a port.
///
/// Args:
///     port: Port number to watch
///     host: Host to connect to (default: "127.0.0.1")
///     timeout: Maximum seconds to wait (default: 30)
///     interval: Seconds between connection attempts (default: 0.1)
///
/// Returns:
///     True once the port accepts a connection, False on timeout.
///
/// Example:
///     >>> portly.wait_for_server(8000, timeout=30)
///     True
#[pyfunction]
#[pyo3(signature = (port, host="127.0.0.1", timeout=30, interval=0.1))]
fn wait_for_server(py: Python<'_>, port: u16, host: &str, timeout: u64, interval: f64) -> bool {
    if port == 0 {
        return false;
    }
    let host = host.to_string();
    // Release the GIL while polling so other Python threads can run.
    py.detach(move || {
        use std::net::{SocketAddr, TcpStream, ToSocketAddrs};
        use std::time::{Duration, Instant};

        // Resolve once; empty means the host is invalid -> cannot accept.
        let addrs: Vec<SocketAddr> = match format!("{host}:{port}").to_socket_addrs() {
            Ok(addrs) => addrs.collect(),
            Err(_) => return false,
        };
        if addrs.is_empty() {
            return false;
        }

        // Per-attempt connect timeout: short enough that a silent host does not
        // hold up the whole timeout, generous enough for a slow accept backlog.
        let attempt_timeout = Duration::from_secs(1);
        let poll_interval = Duration::try_from_secs_f64(interval.max(0.0)).unwrap_or(Duration::MAX);

        let timeout = Duration::from_secs(timeout);
        let started = Instant::now();
        let accepts = || {
            addrs
                .iter()
                .any(|addr| TcpStream::connect_timeout(addr, attempt_timeout).is_ok())
        };

        loop {
            if accepts() {
                return true;
            }

            let remaining = timeout.saturating_sub(started.elapsed());
            if remaining.is_zero() {
                return false;
            }
            std::thread::sleep(poll_interval.min(remaining));
        }
    })
}

// =============================================================================
// FIND FREE IN RANGE
// =============================================================================

/// Find free port(s) within a range.
///
/// Args:
///     lo: Lower bound of the range, inclusive (default: 1024)
///     hi: Upper bound of the range, inclusive (default: 65535)
///     count: Number of distinct free ports to find (default: 1)
///
/// Returns:
///     A free port number when count is 1, otherwise a list of distinct free
///     port numbers within `[lo, hi]`.
///
/// Raises:
///     ValueError: If the range is invalid (`lo > hi`).
///     OSError: If fewer than `count` free ports exist in the range.
///
/// Example:
///     >>> portly.find_free_in_range(8000, 8100)
///     8003
///     >>> portly.find_free_in_range(8000, 8100, count=3)
///     [8003, 8004, 8007]
#[pyfunction]
#[pyo3(signature = (lo=1024, hi=65535, count=1))]
fn find_free_in_range(py: Python<'_>, lo: u16, hi: u16, count: u16) -> PyResult<Py<PyAny>> {
    if lo > hi {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "lo ({lo}) must be <= hi ({hi})"
        )));
    }
    if count == 0 {
        return Vec::<u16>::new().into_py_any(py);
    }
    let found = ports::find_free_ports_in_range(lo, hi, count as usize);
    if found.len() < count as usize {
        return Err(pyo3::exceptions::PyOSError::new_err(format!(
            "Could not find {count} free port(s) in range [{lo}, {hi}]"
        )));
    }
    if count == 1 {
        Ok(found[0].into_py_any(py)?)
    } else {
        Ok(found.into_py_any(py)?)
    }
}

// =============================================================================
// GET PROCESS INFO
// =============================================================================

/// Get information about the process using a port.
///
/// Args:
///     port: Port number to investigate
///
/// Returns:
///     Dict with pid, name, and cmd keys, or None if the port is free
///     (or its owner is not visible to us, e.g. it belongs to another user).
///
/// Note:
///     `cmd` is the full command line on Linux, the executable path on
///     macOS, and the executable name on Windows.
///
/// Example:
///     >>> portly.get_info(8000)
///     {'pid': 1234, 'name': 'python', 'cmd': 'python app.py'}
///     >>> portly.get_info(9999)
///     None
#[pyfunction]
fn get_info(py: Python<'_>, port: u16) -> Option<HashMap<String, Py<PyAny>>> {
    if port == 0 || ports::is_port_free(port) {
        return None;
    }

    // Socket-table scans can block on /proc or process enumeration; release
    // the GIL so other Python threads can run while we look.
    let process = py.detach(move || probe::find_processes(port, true).into_iter().next());

    process.map(|p| info_dict(py, &p))
}

// =============================================================================
// KILL PROCESS
// =============================================================================

/// Kill the process(es) using a port.
///
/// Args:
///     port: Port number
///     force: If True, use SIGKILL (SIGTERM if False). Default: False.
///            On Windows the process is always terminated forcefully.
///
/// Returns:
///     True if the port became free (or was already free)
///
/// Raises:
///     PermissionError: If insufficient permissions
///     OSError: If kill failed for another reason
///
/// Example:
///     >>> portly.kill(8000)
///     True
///     >>> portly.kill(8000, force=True)
///     True
#[pyfunction]
#[pyo3(signature = (port, force=false))]
fn kill(py: Python<'_>, port: u16, force: bool) -> PyResult<bool> {
    if port == 0 || ports::is_port_free(port) {
        return Ok(true);
    }

    let freed = py.detach(move || kill_mod::kill_on_port(port, force));

    match freed {
        Ok(true) => Ok(true),
        Ok(false) => Err(pyo3::exceptions::PyOSError::new_err(format!(
            "Could not free port {port}: no matching process was found or it did not exit"
        ))),
        Err(KillError::Permission) => Err(pyo3::exceptions::PyPermissionError::new_err(format!(
            "Permission denied to kill the process(es) using port {port} \
             (try running with elevated privileges)"
        ))),
        Err(KillError::Other(msg)) => Err(pyo3::exceptions::PyOSError::new_err(msg)),
    }
}

// =============================================================================
// SCAN MULTIPLE PORTS
// =============================================================================

/// Scan multiple ports and return info for each.
///
/// Args:
///     ports: List of port numbers
///
/// Returns:
///     Dict mapping port numbers to process info (or None if free)
///
/// Example:
///     >>> portly.scan([8000, 8001, 5432])
///     {8000: {'pid': 1234, 'name': 'python', 'cmd': 'python app.py'}, 8001: None, 5432: None}
#[pyfunction]
fn scan(py: Python<'_>, ports: Vec<u16>) -> HashMap<u16, Option<HashMap<String, Py<PyAny>>>> {
    ports.into_iter().map(|p| (p, get_info(py, p))).collect()
}

// =============================================================================
// MODULE REGISTRATION
// =============================================================================

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(is_available, m)?)?;
    m.add_function(wrap_pyfunction!(find_free, m)?)?;
    m.add_function(wrap_pyfunction!(find_free_in_range, m)?)?;
    m.add_function(wrap_pyfunction!(wait_until_free, m)?)?;
    m.add_function(wrap_pyfunction!(wait_for_server, m)?)?;
    m.add_function(wrap_pyfunction!(get_info, m)?)?;
    m.add_function(wrap_pyfunction!(kill, m)?)?;
    m.add_function(wrap_pyfunction!(scan, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
