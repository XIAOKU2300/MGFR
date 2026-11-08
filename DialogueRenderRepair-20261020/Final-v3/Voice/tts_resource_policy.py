"""Bound CPU competition of a TTS subprocess created by this launcher only."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import subprocess

def configure_owned_tts(child:subprocess.Popen,logical_budget=4,idle_priority=False):
    if not isinstance(child,subprocess.Popen) or not 1<=logical_budget<=4:
        raise ValueError('Expected an owned bounded TTS subprocess')
    if os.name!='nt':return {'affinityApplied':False,'reason':'non_windows'}
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    kernel.GetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]
    kernel.GetProcessAffinityMask.restype=wintypes.BOOL
    kernel.SetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.c_size_t]
    kernel.SetProcessAffinityMask.restype=wintypes.BOOL
    allowed=ctypes.c_size_t();system=ctypes.c_size_t()
    if not kernel.GetProcessAffinityMask(kernel.GetCurrentProcess(),ctypes.byref(allowed),ctypes.byref(system)):
        raise RuntimeError('Cannot read the launcher CPU allowance')
    cpus=[i for i in range(ctypes.sizeof(ctypes.c_size_t)*8) if allowed.value&(1<<i)]
    if len(cpus)<=8:return {'affinityApplied':False,'reason':'small_cpu_allowance'}
    selected=cpus[-logical_budget:]
    mask=sum(1<<i for i in selected)
    if not mask or mask&~allowed.value:raise RuntimeError('Invalid bounded CPU mask')
    # Popen's process handle belongs to this newly created child. No process lookup,
    # privilege changes, affinity changes to Unity, or global environment changes.
    if not kernel.SetProcessAffinityMask(wintypes.HANDLE(int(child._handle)),ctypes.c_size_t(mask)):
        raise RuntimeError('Cannot apply owned TTS CPU budget')
    if idle_priority:
        kernel.SetPriorityClass.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        kernel.SetPriorityClass.restype=wintypes.BOOL
        if not kernel.SetPriorityClass(wintypes.HANDLE(int(child._handle)),subprocess.IDLE_PRIORITY_CLASS):
            raise RuntimeError('Cannot lower owned TTS scheduling priority')
    return {'affinityApplied':True,'logicalBudget':len(selected),'launcherLogicalCpus':len(cpus),'priority':'IDLE' if idle_priority else 'unchanged'}
