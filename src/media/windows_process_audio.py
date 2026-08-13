from __future__ import annotations

import ctypes
import threading
import time

from array import array
from collections import deque
from ctypes import (
    POINTER,
    Structure,
    Union,
    byref,
    c_int,
    c_longlong,
    c_size_t,
    c_ubyte,
    c_uint32,
    c_uint64,
    c_void_p,
    cast,
    sizeof,
)
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable

import comtypes

from comtypes import (
    COMObject,
    GUID,
    HRESULT,
    IUnknown,
    STDMETHOD,
)

from src.media.audio_spectrum import (
    SPECTRUM_BAND_FREQUENCIES,
    SpectrumAnalyzer,
)


BYTE = c_ubyte
UINT32 = c_uint32
UINT64 = c_uint64
REFERENCE_TIME = c_longlong


S_OK = 0

VT_BLOB = 65

AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK = 1

PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE = 0

AUDCLNT_SHAREMODE_SHARED = 0

AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000
AUDCLNT_STREAMFLAGS_EVENTCALLBACK = 0x00040000
AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM = 0x80000000

AUDCLNT_BUFFERFLAGS_SILENT = 0x00000002

WAVE_FORMAT_PCM = 1

WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102

SYNCHRONIZE = 0x00100000

TH32CS_SNAPPROCESS = 0x00000002
MAX_PATH = 260

INVALID_HANDLE_VALUE = (
    ctypes.c_void_p(
        -1
    ).value
)

VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK = (
    "VAD\\Process_Loopback"
)

CAPTURE_SAMPLE_RATE = 44100
CAPTURE_CHANNELS = 2
CAPTURE_BITS = 16

ANALYSIS_SAMPLE_COUNT = 1024
ANALYSIS_RATE_HZ = 30.0
ANALYSIS_INTERVAL_SECONDS = (
    1.0
    / ANALYSIS_RATE_HZ
)

DEFAULT_RETRY_INTERVAL_SECONDS = 0.75
DEFAULT_STOP_TIMEOUT_SECONDS = 5.0

_ZERO_LEVELS = tuple(
    0.0
    for _ in SPECTRUM_BAND_FREQUENCIES
)


@dataclass(
    frozen=True,
    slots=True,
)
class ProcessInfo:
    process_id: int
    parent_process_id: int
    executable_name: str


class PROCESSENTRY32W(
    Structure
):
    _fields_ = [
        (
            "dwSize",
            wintypes.DWORD,
        ),
        (
            "cntUsage",
            wintypes.DWORD,
        ),
        (
            "th32ProcessID",
            wintypes.DWORD,
        ),
        (
            "th32DefaultHeapID",
            c_size_t,
        ),
        (
            "th32ModuleID",
            wintypes.DWORD,
        ),
        (
            "cntThreads",
            wintypes.DWORD,
        ),
        (
            "th32ParentProcessID",
            wintypes.DWORD,
        ),
        (
            "pcPriClassBase",
            wintypes.LONG,
        ),
        (
            "dwFlags",
            wintypes.DWORD,
        ),
        (
            "szExeFile",
            wintypes.WCHAR
            * MAX_PATH,
        ),
    ]


class WAVEFORMATEX(
    Structure
):
    _fields_ = [
        (
            "wFormatTag",
            wintypes.WORD,
        ),
        (
            "nChannels",
            wintypes.WORD,
        ),
        (
            "nSamplesPerSec",
            wintypes.DWORD,
        ),
        (
            "nAvgBytesPerSec",
            wintypes.DWORD,
        ),
        (
            "nBlockAlign",
            wintypes.WORD,
        ),
        (
            "wBitsPerSample",
            wintypes.WORD,
        ),
        (
            "cbSize",
            wintypes.WORD,
        ),
    ]


class AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS(
    Structure
):
    _fields_ = [
        (
            "TargetProcessId",
            wintypes.DWORD,
        ),
        (
            "ProcessLoopbackMode",
            c_int,
        ),
    ]


class AUDIOCLIENT_ACTIVATION_UNION(
    Union
):
    _fields_ = [
        (
            "ProcessLoopbackParams",
            AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS,
        ),
    ]


class AUDIOCLIENT_ACTIVATION_PARAMS(
    Structure
):
    _anonymous_ = (
        "value",
    )

    _fields_ = [
        (
            "ActivationType",
            c_int,
        ),
        (
            "value",
            AUDIOCLIENT_ACTIVATION_UNION,
        ),
    ]


class BLOB(
    Structure
):
    _fields_ = [
        (
            "cbSize",
            wintypes.ULONG,
        ),
        (
            "pBlobData",
            POINTER(
                BYTE
            ),
        ),
    ]


class PROPVARIANT_VALUE(
    Union
):
    _fields_ = [
        (
            "blob",
            BLOB,
        ),
        (
            "_pointer_size",
            c_void_p,
        ),
        (
            "_64bit_size",
            c_uint64,
        ),
    ]


class PROPVARIANT(
    Structure
):
    _anonymous_ = (
        "value",
    )

    _fields_ = [
        (
            "vt",
            wintypes.WORD,
        ),
        (
            "wReserved1",
            wintypes.WORD,
        ),
        (
            "wReserved2",
            wintypes.WORD,
        ),
        (
            "wReserved3",
            wintypes.WORD,
        ),
        (
            "value",
            PROPVARIANT_VALUE,
        ),
    ]


class IAudioClient(
    IUnknown
):
    _iid_ = GUID(
        "{1CB9AD4C-DBFA-4C32-B178-C2F568A703B2}"
    )


IAudioClient._methods_ = [
    STDMETHOD(
        HRESULT,
        "Initialize",
        (
            c_int,
            wintypes.DWORD,
            REFERENCE_TIME,
            REFERENCE_TIME,
            POINTER(
                WAVEFORMATEX
            ),
            POINTER(
                GUID
            ),
        ),
    ),
    STDMETHOD(
        HRESULT,
        "GetBufferSize",
        (
            POINTER(
                UINT32
            ),
        ),
    ),
    STDMETHOD(
        HRESULT,
        "GetStreamLatency",
        (
            POINTER(
                REFERENCE_TIME
            ),
        ),
    ),
    STDMETHOD(
        HRESULT,
        "GetCurrentPadding",
        (
            POINTER(
                UINT32
            ),
        ),
    ),
    STDMETHOD(
        HRESULT,
        "IsFormatSupported",
        (
            c_int,
            POINTER(
                WAVEFORMATEX
            ),
            POINTER(
                POINTER(
                    WAVEFORMATEX
                )
            ),
        ),
    ),
    STDMETHOD(
        HRESULT,
        "GetMixFormat",
        (
            POINTER(
                POINTER(
                    WAVEFORMATEX
                )
            ),
        ),
    ),
    STDMETHOD(
        HRESULT,
        "GetDevicePeriod",
        (
            POINTER(
                REFERENCE_TIME
            ),
            POINTER(
                REFERENCE_TIME
            ),
        ),
    ),
    STDMETHOD(
        HRESULT,
        "Start",
        (),
    ),
    STDMETHOD(
        HRESULT,
        "Stop",
        (),
    ),
    STDMETHOD(
        HRESULT,
        "Reset",
        (),
    ),
    STDMETHOD(
        HRESULT,
        "SetEventHandle",
        (
            wintypes.HANDLE,
        ),
    ),
    STDMETHOD(
        HRESULT,
        "GetService",
        (
            POINTER(
                GUID
            ),
            POINTER(
                c_void_p
            ),
        ),
    ),
]


class IAudioCaptureClient(
    IUnknown
):
    _iid_ = GUID(
        "{C8ADBD64-E71E-48A0-A4DE-185C395CD317}"
    )


IAudioCaptureClient._methods_ = [
    STDMETHOD(
        HRESULT,
        "GetBuffer",
        (
            POINTER(
                POINTER(
                    BYTE
                )
            ),
            POINTER(
                UINT32
            ),
            POINTER(
                wintypes.DWORD
            ),
            POINTER(
                UINT64
            ),
            POINTER(
                UINT64
            ),
        ),
    ),
    STDMETHOD(
        HRESULT,
        "ReleaseBuffer",
        (
            UINT32,
        ),
    ),
    STDMETHOD(
        HRESULT,
        "GetNextPacketSize",
        (
            POINTER(
                UINT32
            ),
        ),
    ),
]


class IActivateAudioInterfaceAsyncOperation(
    IUnknown
):
    _iid_ = GUID(
        "{72A22D78-CDE4-431D-B8CC-843A71199B6D}"
    )


IActivateAudioInterfaceAsyncOperation._methods_ = [
    STDMETHOD(
        HRESULT,
        "GetActivateResult",
        (
            POINTER(
                HRESULT
            ),
            POINTER(
                POINTER(
                    IUnknown
                )
            ),
        ),
    ),
]


class IActivateAudioInterfaceCompletionHandler(
    IUnknown
):
    _iid_ = GUID(
        "{41D949AB-9862-444A-80F6-C261334DA5EB}"
    )


IActivateAudioInterfaceCompletionHandler._methods_ = [
    STDMETHOD(
        HRESULT,
        "ActivateCompleted",
        (
            POINTER(
                IActivateAudioInterfaceAsyncOperation
            ),
        ),
    ),
]


class IAgileObject(
    IUnknown
):
    _iid_ = GUID(
        "{94EA2B94-E9CC-49E0-C0FF-EE64CA8F5B90}"
    )

    _methods_ = []


class _ActivationHandler(
    COMObject
):
    _com_interfaces_ = [
        IActivateAudioInterfaceCompletionHandler,
        IAgileObject,
    ]

    def __init__(
        self,
    ):
        super().__init__()

        self.completed = (
            threading.Event()
        )

        self.audio_client = None
        self.error = None

    def ActivateCompleted(
        self,
        this,
        operation,
    ):
        try:
            activation_result = (
                HRESULT()
            )

            activated_interface = (
                POINTER(
                    IUnknown
                )()
            )

            call_result = (
                operation.GetActivateResult(
                    byref(
                        activation_result
                    ),
                    byref(
                        activated_interface
                    ),
                )
            )

            if _failed(
                call_result
            ):
                raise RuntimeError(
                    "GetActivateResult failed: "
                    + _hr_hex(
                        call_result
                    )
                )

            if _failed(
                activation_result.value
            ):
                raise RuntimeError(
                    "Audio activation failed: "
                    + _hr_hex(
                        activation_result.value
                    )
                )

            self.audio_client = (
                activated_interface.QueryInterface(
                    IAudioClient
                )
            )

        except BaseException as error:
            self.error = error

        finally:
            self.completed.set()

        return S_OK


def _failed(
    value,
) -> bool:
    return ctypes.c_long(
        int(
            value
        )
    ).value < 0


def _hr_hex(
    value,
) -> str:
    return (
        "0x"
        + format(
            int(
                value
            )
            & 0xFFFFFFFF,
            "08X",
        )
    )


def _configure_kernel32():
    kernel32 = ctypes.WinDLL(
        "kernel32.dll",
        use_last_error=True,
    )

    kernel32.CreateToolhelp32Snapshot.argtypes = [
        wintypes.DWORD,
        wintypes.DWORD,
    ]

    kernel32.CreateToolhelp32Snapshot.restype = (
        wintypes.HANDLE
    )

    kernel32.Process32FirstW.argtypes = [
        wintypes.HANDLE,
        POINTER(
            PROCESSENTRY32W
        ),
    ]

    kernel32.Process32FirstW.restype = (
        wintypes.BOOL
    )

    kernel32.Process32NextW.argtypes = [
        wintypes.HANDLE,
        POINTER(
            PROCESSENTRY32W
        ),
    ]

    kernel32.Process32NextW.restype = (
        wintypes.BOOL
    )

    kernel32.CreateEventW.argtypes = [
        c_void_p,
        wintypes.BOOL,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    ]

    kernel32.CreateEventW.restype = (
        wintypes.HANDLE
    )

    kernel32.OpenProcess.argtypes = [
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]

    kernel32.OpenProcess.restype = (
        wintypes.HANDLE
    )

    kernel32.WaitForSingleObject.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
    ]

    kernel32.WaitForSingleObject.restype = (
        wintypes.DWORD
    )

    kernel32.CloseHandle.argtypes = [
        wintypes.HANDLE,
    ]

    kernel32.CloseHandle.restype = (
        wintypes.BOOL
    )

    return kernel32


def enumerate_processes() -> tuple[
    ProcessInfo,
    ...,
]:
    kernel32 = (
        _configure_kernel32()
    )

    snapshot = (
        kernel32.CreateToolhelp32Snapshot(
            TH32CS_SNAPPROCESS,
            0,
        )
    )

    if (
        snapshot is None
        or snapshot
        == INVALID_HANDLE_VALUE
    ):
        raise ctypes.WinError(
            ctypes.get_last_error()
        )

    processes = []

    try:
        entry = (
            PROCESSENTRY32W()
        )

        entry.dwSize = sizeof(
            PROCESSENTRY32W
        )

        success = (
            kernel32.Process32FirstW(
                snapshot,
                byref(
                    entry
                ),
            )
        )

        while success:
            processes.append(
                ProcessInfo(
                    process_id=int(
                        entry.th32ProcessID
                    ),
                    parent_process_id=int(
                        entry.th32ParentProcessID
                    ),
                    executable_name=str(
                        entry.szExeFile
                    ),
                )
            )

            entry.dwSize = sizeof(
                PROCESSENTRY32W
            )

            success = (
                kernel32.Process32NextW(
                    snapshot,
                    byref(
                        entry
                    ),
                )
            )

    finally:
        kernel32.CloseHandle(
            snapshot
        )

    return tuple(
        processes
    )


def select_process_tree_root(
    processes,
    executable_name: str,
) -> int | None:
    target_name = str(
        executable_name
        or ""
    ).strip().casefold()

    if not target_name:
        raise ValueError(
            "executable_name is required"
        )

    matches = tuple(
        process
        for process in processes
        if str(
            process.executable_name
            or ""
        ).casefold()
        == target_name
    )

    if not matches:
        return None

    process_ids = {
        int(
            process.process_id
        )
        for process in matches
    }

    roots = tuple(
        process
        for process in matches
        if int(
            process.parent_process_id
        )
        not in process_ids
    )

    if len(
        roots
    ) != 1:
        return None

    root_id = int(
        roots[0].process_id
    )

    if root_id <= 0:
        return None

    return root_id


def find_spotify_root_process_id() -> int | None:
    return select_process_tree_root(
        enumerate_processes(),
        "Spotify.exe",
    )


def _make_capture_format() -> WAVEFORMATEX:
    capture_format = (
        WAVEFORMATEX()
    )

    capture_format.wFormatTag = (
        WAVE_FORMAT_PCM
    )

    capture_format.nChannels = (
        CAPTURE_CHANNELS
    )

    capture_format.nSamplesPerSec = (
        CAPTURE_SAMPLE_RATE
    )

    capture_format.wBitsPerSample = (
        CAPTURE_BITS
    )

    capture_format.nBlockAlign = int(
        CAPTURE_CHANNELS
        * CAPTURE_BITS
        / 8
    )

    capture_format.nAvgBytesPerSec = int(
        CAPTURE_SAMPLE_RATE
        * capture_format.nBlockAlign
    )

    capture_format.cbSize = 0

    return capture_format


def _activate_process_loopback(
    process_id: int,
):
    activation_params = (
        AUDIOCLIENT_ACTIVATION_PARAMS()
    )

    activation_params.ActivationType = (
        AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK
    )

    activation_params.ProcessLoopbackParams.TargetProcessId = (
        int(
            process_id
        )
    )

    activation_params.ProcessLoopbackParams.ProcessLoopbackMode = (
        PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE
    )

    activation_blob = (
        BYTE
        * sizeof(
            activation_params
        )
    ).from_buffer_copy(
        activation_params
    )

    propvariant = (
        PROPVARIANT()
    )

    propvariant.vt = (
        VT_BLOB
    )

    propvariant.blob.cbSize = (
        sizeof(
            activation_params
        )
    )

    propvariant.blob.pBlobData = (
        cast(
            activation_blob,
            POINTER(
                BYTE
            ),
        )
    )

    handler = (
        _ActivationHandler()
    )

    handler_interface = (
        handler.QueryInterface(
            IActivateAudioInterfaceCompletionHandler
        )
    )

    async_operation = POINTER(
        IActivateAudioInterfaceAsyncOperation
    )()

    mmdevapi = ctypes.WinDLL(
        "Mmdevapi.dll"
    )

    activate = (
        mmdevapi.ActivateAudioInterfaceAsync
    )

    activate.argtypes = [
        wintypes.LPCWSTR,
        POINTER(
            GUID
        ),
        POINTER(
            PROPVARIANT
        ),
        POINTER(
            IActivateAudioInterfaceCompletionHandler
        ),
        POINTER(
            POINTER(
                IActivateAudioInterfaceAsyncOperation
            )
        ),
    ]

    activate.restype = HRESULT

    result = activate(
        VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK,
        byref(
            IAudioClient._iid_
        ),
        byref(
            propvariant
        ),
        handler_interface,
        byref(
            async_operation
        ),
    )

    if _failed(
        result
    ):
        raise RuntimeError(
            "ActivateAudioInterfaceAsync failed: "
            + _hr_hex(
                result
            )
        )

    if not handler.completed.wait(
        timeout=8.0
    ):
        raise RuntimeError(
            "Timed out waiting for audio activation."
        )

    if handler.error is not None:
        raise handler.error

    if handler.audio_client is None:
        raise RuntimeError(
            "Activation completed without IAudioClient."
        )

    keepalive = (
        async_operation,
        handler,
        handler_interface,
        activation_blob,
        propvariant,
    )

    return (
        handler.audio_client,
        keepalive,
    )


def _drain_capture_packets(
    capture_client,
    capture_format,
    pending,
) -> None:
    while True:
        packet_size = (
            UINT32()
        )

        result = (
            capture_client.GetNextPacketSize(
                byref(
                    packet_size
                )
            )
        )

        if _failed(
            result
        ):
            raise RuntimeError(
                "GetNextPacketSize failed: "
                + _hr_hex(
                    result
                )
            )

        if packet_size.value == 0:
            return

        data = POINTER(
            BYTE
        )()

        frames = UINT32()
        flags = wintypes.DWORD()
        device_position = UINT64()
        qpc_position = UINT64()

        result = capture_client.GetBuffer(
            byref(
                data
            ),
            byref(
                frames
            ),
            byref(
                flags
            ),
            byref(
                device_position
            ),
            byref(
                qpc_position
            ),
        )

        if _failed(
            result
        ):
            raise RuntimeError(
                "GetBuffer failed: "
                + _hr_hex(
                    result
                )
            )

        packet_frames = int(
            frames.value
        )

        try:
            if (
                flags.value
                & AUDCLNT_BUFFERFLAGS_SILENT
            ):
                for _ in range(
                    packet_frames
                ):
                    pending.append(
                        0.0
                    )

            else:
                byte_count = int(
                    packet_frames
                    * capture_format.nBlockAlign
                )

                raw = ctypes.string_at(
                    data,
                    byte_count,
                )

                pcm = array(
                    "h"
                )

                pcm.frombytes(
                    raw
                )

                for index in range(
                    0,
                    len(
                        pcm
                    )
                    - 1,
                    2,
                ):
                    left = float(
                        pcm[index]
                    )

                    right = float(
                        pcm[
                            index + 1
                        ]
                    )

                    mono = (
                        left
                        + right
                    ) / 65536.0

                    pending.append(
                        mono
                    )

        finally:
            release_result = (
                capture_client.ReleaseBuffer(
                    frames
                )
            )

            if _failed(
                release_result
            ):
                raise RuntimeError(
                    "ReleaseBuffer failed: "
                    + _hr_hex(
                        release_result
                    )
                )


def _capture_process_spectrum(
    process_id: int,
    stop_event: threading.Event,
    publish_levels: Callable[
        [tuple[float, ...]],
        None,
    ],
) -> None:
    if int(
        process_id
    ) <= 0:
        raise ValueError(
            "process_id must be positive"
        )

    (
        audio_client,
        activation_keepalive,
    ) = _activate_process_loopback(
        process_id
    )

    capture_format = (
        _make_capture_format()
    )

    stream_flags = (
        AUDCLNT_STREAMFLAGS_LOOPBACK
        | AUDCLNT_STREAMFLAGS_EVENTCALLBACK
        | AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM
    )

    result = audio_client.Initialize(
        AUDCLNT_SHAREMODE_SHARED,
        stream_flags,
        0,
        0,
        byref(
            capture_format
        ),
        None,
    )

    if _failed(
        result
    ):
        raise RuntimeError(
            "IAudioClient.Initialize failed: "
            + _hr_hex(
                result
            )
        )

    capture_pointer = (
        c_void_p()
    )

    result = audio_client.GetService(
        byref(
            IAudioCaptureClient._iid_
        ),
        byref(
            capture_pointer
        ),
    )

    if _failed(
        result
    ):
        raise RuntimeError(
            "IAudioClient.GetService failed: "
            + _hr_hex(
                result
            )
        )

    if not capture_pointer.value:
        raise RuntimeError(
            "GetService returned null capture client."
        )

    capture_client = cast(
        capture_pointer,
        POINTER(
            IAudioCaptureClient
        ),
    )

    kernel32 = (
        _configure_kernel32()
    )

    event_handle = (
        kernel32.CreateEventW(
            None,
            False,
            False,
            None,
        )
    )

    if not event_handle:
        raise ctypes.WinError(
            ctypes.get_last_error()
        )

    process_handle = (
        kernel32.OpenProcess(
            SYNCHRONIZE,
            False,
            int(
                process_id
            ),
        )
    )

    if not process_handle:
        kernel32.CloseHandle(
            event_handle
        )

        raise RuntimeError(
            "Target process is no longer available."
        )

    started = False

    analyzer = (
        SpectrumAnalyzer()
    )

    pending = deque(
        maxlen=ANALYSIS_SAMPLE_COUNT
    )

    last_analysis = 0.0

    try:
        result = (
            audio_client.SetEventHandle(
                event_handle
            )
        )

        if _failed(
            result
        ):
            raise RuntimeError(
                "SetEventHandle failed: "
                + _hr_hex(
                    result
                )
            )

        result = audio_client.Start()

        if _failed(
            result
        ):
            raise RuntimeError(
                "IAudioClient.Start failed: "
                + _hr_hex(
                    result
                )
            )

        started = True

        while not stop_event.is_set():
            process_state = (
                kernel32.WaitForSingleObject(
                    process_handle,
                    0,
                )
            )

            if process_state == WAIT_OBJECT_0:
                return

            wait_result = (
                kernel32.WaitForSingleObject(
                    event_handle,
                    100,
                )
            )

            if wait_result == WAIT_TIMEOUT:
                continue

            if wait_result != WAIT_OBJECT_0:
                raise RuntimeError(
                    "Audio event wait failed."
                )

            _drain_capture_packets(
                capture_client,
                capture_format,
                pending,
            )

            now = time.perf_counter()

            if (
                len(
                    pending
                )
                == ANALYSIS_SAMPLE_COUNT
                and (
                    now
                    - last_analysis
                )
                >= ANALYSIS_INTERVAL_SECONDS
            ):
                levels = analyzer.analyze(
                    tuple(
                        pending
                    ),
                    CAPTURE_SAMPLE_RATE,
                )

                publish_levels(
                    levels
                )

                last_analysis = now

    finally:
        if started:
            stop_result = (
                audio_client.Stop()
            )

            if _failed(
                stop_result
            ):
                pass

        kernel32.CloseHandle(
            process_handle
        )

        kernel32.CloseHandle(
            event_handle
        )

        del activation_keepalive


def _initialize_worker_com() -> None:
    comtypes.CoInitializeEx(
        comtypes.COINIT_MULTITHREADED
    )


def _uninitialize_worker_com() -> None:
    comtypes.CoUninitialize()


class SpotifyAudioSpectrumService:
    """
    Background Spotify-only spectrum capture.

    The service owns a dedicated Python worker thread and
    its MTA COM apartment. It finds the Spotify root
    process, captures that process tree using Windows
    process loopback, analyzes the samples, and exposes
    only eight normalized spectrum values.

    Audio samples are never written to disk and are not
    exposed outside the capture worker.
    """

    def __init__(
        self,
        *,
        retry_interval_seconds: float = (
            DEFAULT_RETRY_INTERVAL_SECONDS
        ),
        process_finder: Callable[
            [],
            int | None,
        ] | None = None,
        capture_runner=None,
        com_initializer=None,
        com_uninitializer=None,
    ):
        retry_interval = float(
            retry_interval_seconds
        )

        if retry_interval <= 0.0:
            raise ValueError(
                "retry_interval_seconds must be positive"
            )

        self._retry_interval_seconds = (
            retry_interval
        )

        self._process_finder = (
            process_finder
            or find_spotify_root_process_id
        )

        self._capture_runner = (
            capture_runner
            or _capture_process_spectrum
        )

        self._com_initializer = (
            com_initializer
            or _initialize_worker_com
        )

        self._com_uninitializer = (
            com_uninitializer
            or _uninitialize_worker_com
        )

        self._lock = (
            threading.RLock()
        )

        self._stop_event = (
            threading.Event()
        )

        self._thread = None

        self._running = False

        self._target_process_id = None

        self._latest_levels = (
            _ZERO_LEVELS
        )

        self._last_error = ""

    @property
    def running(
        self,
    ) -> bool:
        with self._lock:
            return bool(
                self._running
            )

    @property
    def target_process_id(
        self,
    ) -> int | None:
        with self._lock:
            return self._target_process_id

    @property
    def latest_levels(
        self,
    ) -> tuple[float, ...]:
        with self._lock:
            return tuple(
                self._latest_levels
            )

    @property
    def last_error(
        self,
    ) -> str:
        with self._lock:
            return str(
                self._last_error
            )

    def start(
        self,
    ) -> bool:
        with self._lock:
            existing = (
                self._thread
            )

            if (
                existing is not None
                and existing.is_alive()
            ):
                return False

            self._stop_event = (
                threading.Event()
            )

            self._latest_levels = (
                _ZERO_LEVELS
            )

            self._last_error = ""

            thread = threading.Thread(
                target=self._worker_main,
                name=(
                    "PresenceSpotifySpectrum"
                ),
                daemon=True,
            )

            self._thread = thread

            thread.start()

            return True

    def stop(
        self,
        timeout_seconds: float = (
            DEFAULT_STOP_TIMEOUT_SECONDS
        ),
    ) -> bool:
        timeout = max(
            0.0,
            float(
                timeout_seconds
            ),
        )

        with self._lock:
            thread = self._thread

            self._stop_event.set()

        if (
            thread is not None
            and thread is not threading.current_thread()
        ):
            thread.join(
                timeout=timeout
            )

        with self._lock:
            stopped = (
                thread is None
                or not thread.is_alive()
            )

            if stopped:
                if self._thread is thread:
                    self._thread = None

                self._running = False
                self._target_process_id = None
                self._latest_levels = (
                    _ZERO_LEVELS
                )

            return stopped

    def shutdown(
        self,
        timeout_seconds: float = (
            DEFAULT_STOP_TIMEOUT_SECONDS
        ),
    ) -> bool:
        return self.stop(
            timeout_seconds=(
                timeout_seconds
            )
        )

    def _publish_levels(
        self,
        levels,
    ) -> None:
        checked = tuple(
            max(
                0.0,
                min(
                    1.0,
                    float(
                        value
                    ),
                ),
            )
            for value in levels
        )

        if len(
            checked
        ) != len(
            SPECTRUM_BAND_FREQUENCIES
        ):
            return

        with self._lock:
            self._latest_levels = (
                checked
            )

    def _set_target_process_id(
        self,
        process_id: int | None,
    ) -> None:
        with self._lock:
            self._target_process_id = (
                process_id
            )

    def _set_error(
        self,
        message,
    ) -> None:
        with self._lock:
            self._last_error = str(
                message
                or ""
            )

    def _clear_levels(
        self,
    ) -> None:
        with self._lock:
            self._latest_levels = (
                _ZERO_LEVELS
            )

    def _wait_retry(
        self,
    ) -> bool:
        return self._stop_event.wait(
            self._retry_interval_seconds
        )

    def _worker_main(
        self,
    ) -> None:
        initialized = False

        with self._lock:
            self._running = True

        try:
            self._com_initializer()

            initialized = True

            while not self._stop_event.is_set():
                process_id = (
                    self._process_finder()
                )

                if (
                    process_id is None
                    or int(
                        process_id
                    )
                    <= 0
                ):
                    self._set_target_process_id(
                        None
                    )

                    self._clear_levels()

                    if self._wait_retry():
                        break

                    continue

                process_id = int(
                    process_id
                )

                self._set_target_process_id(
                    process_id
                )

                self._set_error(
                    ""
                )

                try:
                    self._capture_runner(
                        process_id,
                        self._stop_event,
                        self._publish_levels,
                    )

                except BaseException as error:
                    if not self._stop_event.is_set():
                        self._set_error(
                            str(
                                error
                            )
                            or repr(
                                error
                            )
                        )

                finally:
                    self._set_target_process_id(
                        None
                    )

                    self._clear_levels()

                if self._stop_event.is_set():
                    break

                if self._wait_retry():
                    break

        except BaseException as error:
            if not self._stop_event.is_set():
                self._set_error(
                    str(
                        error
                    )
                    or repr(
                        error
                    )
                )

        finally:
            if initialized:
                try:
                    self._com_uninitializer()

                except BaseException:
                    pass

            with self._lock:
                self._running = False
                self._target_process_id = None
                self._latest_levels = (
                    _ZERO_LEVELS
                )