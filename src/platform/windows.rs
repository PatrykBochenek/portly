use crate::model::{KillError, PortProcess};
use std::collections::{HashMap, HashSet};
use std::ptr::addr_of;
use std::slice;
use windows_sys::Win32::Foundation::{
    CloseHandle, GetLastError, ERROR_ACCESS_DENIED, ERROR_INSUFFICIENT_BUFFER, FALSE,
    INVALID_HANDLE_VALUE, NO_ERROR,
};
use windows_sys::Win32::NetworkManagement::IpHelper::{
    GetExtendedTcpTable, GetExtendedUdpTable, MIB_TCP6ROW_OWNER_PID, MIB_TCP6TABLE_OWNER_PID,
    MIB_TCPROW_OWNER_PID, MIB_TCPTABLE_OWNER_PID, MIB_TCP_STATE_LISTEN, MIB_UDP6ROW_OWNER_PID,
    MIB_UDP6TABLE_OWNER_PID, MIB_UDPROW_OWNER_PID, MIB_UDPTABLE_OWNER_PID, TCP_TABLE_OWNER_PID_ALL,
    UDP_TABLE_OWNER_PID,
};
use windows_sys::Win32::Networking::WinSock::{AF_INET, AF_INET6};
use windows_sys::Win32::System::Diagnostics::ToolHelp::{
    CreateToolhelp32Snapshot, Process32First, Process32Next, PROCESSENTRY32, TH32CS_SNAPPROCESS,
};
use windows_sys::Win32::System::Threading::{OpenProcess, TerminateProcess, PROCESS_TERMINATE};

/// Scan one Win32 "extended table" for rows matching `port` and record
/// their owning PIDs in `pids`.
///
/// `$matches` receives each row and decides whether it belongs to `port`
/// (and, for TCP, honours the `listen_only` filter).
macro_rules! scan_table {
    ($getter:path, $family:expr, $class:expr, $table_ty:ty, $row_ty:ty, $port:expr, $pids:expr, $matches:expr) => {{
        let mut size: u32 = 0;
        // u32 buffer: guarantees the 4-byte alignment the MIB tables need.
        let mut buf: Vec<u32> = Vec::new();
        let result = loop {
            let result =
                unsafe { $getter(buf.as_mut_ptr().cast(), &mut size, 0, $family, $class, 0) };
            if result == NO_ERROR {
                break result;
            }
            if result == ERROR_INSUFFICIENT_BUFFER {
                buf.resize((size as usize).div_ceil(4) + 1, 0);
                continue;
            }
            return Err(format!("GetExtendedTable failed: {result:#x}"));
        };
        debug_assert_eq!(result, NO_ERROR);
        unsafe {
            let table = buf.as_ptr() as *const $table_ty;
            let count = addr_of!((*table).dwNumEntries).read_unaligned() as usize;
            let rows: &[$row_ty] = slice::from_raw_parts(addr_of!((*table).table).cast(), count);
            for row in rows {
                if $matches(row) {
                    let pid = row.dwOwningPid;
                    // PID 0 ([System Process]) owns TIME_WAIT rows and PID 4
                    // (System) owns kernel sockets; neither can nor should be
                    // terminated.
                    if pid != 0 && pid != 4 {
                        $pids.insert(pid);
                    }
                }
            }
        }
    }};
}

fn collect_pids(port: u16, listen_only: bool, pids: &mut HashSet<u32>) -> Result<(), String> {
    scan_table!(
        GetExtendedTcpTable,
        AF_INET as u32,
        TCP_TABLE_OWNER_PID_ALL,
        MIB_TCPTABLE_OWNER_PID,
        MIB_TCPROW_OWNER_PID,
        port,
        pids,
        |row: &MIB_TCPROW_OWNER_PID| {
            u16::from_be(row.dwLocalPort as u16) == port
                && (!listen_only || row.dwState == MIB_TCP_STATE_LISTEN as u32)
        }
    );
    scan_table!(
        GetExtendedTcpTable,
        AF_INET6 as u32,
        TCP_TABLE_OWNER_PID_ALL,
        MIB_TCP6TABLE_OWNER_PID,
        MIB_TCP6ROW_OWNER_PID,
        port,
        pids,
        |row: &MIB_TCP6ROW_OWNER_PID| {
            u16::from_be(row.dwLocalPort as u16) == port
                && (!listen_only || row.dwState == MIB_TCP_STATE_LISTEN as u32)
        }
    );
    if !listen_only {
        scan_table!(
            GetExtendedUdpTable,
            AF_INET as u32,
            UDP_TABLE_OWNER_PID,
            MIB_UDPTABLE_OWNER_PID,
            MIB_UDPROW_OWNER_PID,
            port,
            pids,
            |row: &MIB_UDPROW_OWNER_PID| u16::from_be(row.dwLocalPort as u16) == port
        );
        scan_table!(
            GetExtendedUdpTable,
            AF_INET6 as u32,
            UDP_TABLE_OWNER_PID,
            MIB_UDP6TABLE_OWNER_PID,
            MIB_UDP6ROW_OWNER_PID,
            port,
            pids,
            |row: &MIB_UDP6ROW_OWNER_PID| u16::from_be(row.dwLocalPort as u16) == port
        );
    }
    Ok(())
}

/// Snapshot of process-id → executable name (ToolHelp32).
fn snapshot_names() -> Result<HashMap<u32, String>, KillError> {
    let mut names = HashMap::new();
    unsafe {
        let handle = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if handle == INVALID_HANDLE_VALUE {
            return Err(KillError::Other(
                "CreateToolhelp32Snapshot failed".to_string(),
            ));
        }
        let mut entry: PROCESSENTRY32 = std::mem::zeroed();
        entry.dwSize = std::mem::size_of::<PROCESSENTRY32>() as u32;
        if Process32First(handle, &mut entry) == FALSE {
            CloseHandle(handle);
            return Err(KillError::Other("Process32First failed".to_string()));
        }
        loop {
            let len = entry
                .szExeFile
                .iter()
                .position(|&c| c == 0)
                .unwrap_or(entry.szExeFile.len());
            // windows-sys exposes the WCHAR image name as raw bytes.
            let bytes: Vec<u8> = entry.szExeFile[..len].iter().map(|&c| c as u8).collect();
            let name = String::from_utf8_lossy(&bytes).into_owned();
            names.insert(entry.th32ProcessID, name);
            if Process32Next(handle, &mut entry) == FALSE {
                break;
            }
        }
        CloseHandle(handle);
    }
    Ok(names)
}

pub fn find_processes(port: u16, listen_only: bool) -> Vec<PortProcess> {
    let mut pids = HashSet::new();
    if collect_pids(port, listen_only, &mut pids).is_err() {
        return Vec::new();
    }
    if pids.is_empty() {
        return Vec::new();
    }
    let names = snapshot_names().unwrap_or_default();
    pids.into_iter()
        .map(|pid| {
            let name = names
                .get(&pid)
                .cloned()
                .unwrap_or_else(|| "Unknown".to_string());
            // Windows provides no cheap, dependency-free full command
            // line; the executable name is the best we can offer.
            PortProcess {
                pid,
                cmd: name.clone(),
                name,
            }
        })
        .collect()
}

pub fn kill_pid(pid: u32, _force: bool) -> Result<(), KillError> {
    unsafe {
        let handle = OpenProcess(PROCESS_TERMINATE, 0, pid);
        if handle.is_null() {
            // The process may have exited between the scan and now.
            let names = snapshot_names()?;
            if !names.contains_key(&pid) {
                return Ok(());
            }
            let err = GetLastError();
            return Err(if err == ERROR_ACCESS_DENIED {
                KillError::Permission
            } else {
                KillError::Other(format!("Failed to open process {pid}: {err:#x}"))
            });
        }
        let result = TerminateProcess(handle, 0);
        CloseHandle(handle);
        if result == FALSE {
            let err = GetLastError();
            return Err(if err == ERROR_ACCESS_DENIED {
                KillError::Permission
            } else {
                KillError::Other(format!("Failed to terminate process {pid}: {err:#x}"))
            });
        }
    }
    Ok(())
}
