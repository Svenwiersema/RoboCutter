"""Eigen vensterframe: de donkere header van ``MainWindow`` wordt zelf de
titelbalk (zoals VS Code), i.p.v. de standaard Windows-titelbalk erboven.

Op Svens verzoek: "het frame van de venster zelfde style maken als de app
in plaats van standaard windows". Aanpak (bewust níet puur
``FramelessWindowHint`` met zelfgebouwd slepen/resizen):

- Qt krijgt ``FramelessWindowHint`` (zodat Qt zelf geen randen verrekent),
  maar het native venster krijgt de Windows-stijlbits voor een gewoon
  venster terug (``WS_CAPTION``/``WS_THICKFRAME``/min/max). Daardoor houdt
  Windows alles wat een normaal venster gratis krijgt: schaduw, afgeronde
  hoeken (Windows 11), Aero Snap, de minimaliseer-/maximaliseeranimatie en
  minimaliseren door op de taakbalkknop te klikken.
- ``WM_NCCALCSIZE`` zegt dat het hele venster "client" is, dus Windows
  tekent geen eigen titelbalk/rand meer. Gemaximaliseerd valt een venster
  met ``WS_THICKFRAME`` aan elke kant de randdikte buiten het scherm; die
  wordt er hier weer afgehaald.
- ``WM_NCHITTEST`` vertelt Windows waar de (onzichtbare) resize-randen
  zitten en welk deel van de header als titelbalk telt (``HTCAPTION``):
  alles wat geen knop is. Slepen, dubbelklik = maximaliseren, rechtsklik =
  systeemmenu en snap werken daardoor via Windows zelf.
- De maximaliseerknop meldt zich als ``HTMAXBUTTON``: alleen dan toont
  Windows 11 bij hover de schermindelingen-popup (snap layouts). Gevolg:
  Qt krijgt boven die knop geen muisevents meer, maar Windows' niet-client-
  berichten (``WM_NCMOUSEMOVE``/``WM_NCLBUTTONDOWN``/``UP``/
  ``WM_NCMOUSELEAVE``) — die worden hier zelf omgezet naar hover/ingedrukt/
  klik op de knop. Muisbewegingen gaan daarna gewoon door naar Windows (dat
  start er de popup mee); klikken niet, anders tekent Windows er een
  ouderwetse knop overheen. Twee dingen blokkeren de popup (gemeten, met
  een kaal Win32-testvenster als referentie): ``DwmExtendFrameIntoClientArea``
  (dus bewust niet gebruikt) en de ``WS_POPUP``-stijl die Qt een frameloos
  venster geeft (dus weggehaald). Ook rekent ``WM_NCHITTEST`` met het punt
  uit ``lParam``, niet met de muispositie.
- Gemaximaliseerd met een automatisch verbergende taakbalk blijft aan die
  kant 2 px vrij, anders kan de taakbalk niet meer tevoorschijn komen.

Alleen actief op het echte Windows-platform van Qt; bij bijvoorbeeld
``QT_QPA_PLATFORM=offscreen`` (rooktests) doet deze module niets en blijft
het een gewoon Qt-venster.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QAbstractButton, QWidget

from robocutter.ui.widgets.vensterknoppen import VensterKnop

_WM_NCCALCSIZE = 0x0083
_WM_NCHITTEST = 0x0084
_WM_NCMOUSEMOVE = 0x00A0
_WM_NCLBUTTONDOWN = 0x00A1
_WM_NCLBUTTONUP = 0x00A2
_WM_NCLBUTTONDBLCLK = 0x00A3
_WM_NCMOUSELEAVE = 0x02A2

_HTCAPTION = 2
_HTMAXBUTTON = 9
_HTLEFT, _HTRIGHT, _HTTOP, _HTTOPLEFT, _HTTOPRIGHT = 10, 11, 12, 13, 14
_HTBOTTOM, _HTBOTTOMLEFT, _HTBOTTOMRIGHT = 15, 16, 17

_GWL_STYLE = -16
_WS_POPUP = 0x80000000
_WS_CAPTION = 0x00C00000
_WS_THICKFRAME = 0x00040000
_WS_SYSMENU = 0x00080000
_WS_MINIMIZEBOX = 0x00020000
_WS_MAXIMIZEBOX = 0x00010000

_SWP_NOSIZE, _SWP_NOMOVE, _SWP_NOZORDER, _SWP_FRAMECHANGED = 0x1, 0x2, 0x4, 0x20

_SM_CXSIZEFRAME, _SM_CYSIZEFRAME, _SM_CXPADDEDBORDER = 32, 33, 92

_MONITOR_DEFAULTTONEAREST = 2
_ABM_GETSTATE, _ABM_GETAUTOHIDEBAREX = 0x4, 0xB
_ABS_AUTOHIDE = 0x1
_ABE_LEFT, _ABE_TOP, _ABE_RIGHT, _ABE_BOTTOM = 0, 1, 2, 3
# Zoveel pixels blijft gemaximaliseerd vrij aan de kant van een automatisch
# verbergende taakbalk, zodat de muis 'm nog kan laten verschijnen.
_AUTOHIDE_RUIMTE = 2

# Breedte (logische pixels) van de onzichtbare resize-strook langs de rand.
_RESIZE_RAND = 6


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class _APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", wintypes.UINT),
        ("uEdge", wintypes.UINT),
        ("rc", wintypes.RECT),
        ("lParam", wintypes.LPARAM),
    ]


def is_actief() -> bool:
    return sys.platform == "win32" and QGuiApplication.platformName() == "windows"


def installeer(venster: QWidget) -> bool:
    """Zet het eigen frame aan voor ``venster`` (vóór ``show()`` aanroepen).

    Geeft ``False`` terug (en laat het venster ongemoeid) buiten Windows.
    """
    if not is_actief():
        return False
    venster.setWindowFlags(venster.windowFlags() | Qt.WindowType.FramelessWindowHint)
    hwnd = int(venster.winId())

    user32 = ctypes.windll.user32
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    stijl = user32.GetWindowLongPtrW(hwnd, _GWL_STYLE)
    stijl |= _WS_CAPTION | _WS_THICKFRAME | _WS_SYSMENU | _WS_MINIMIZEBOX | _WS_MAXIMIZEBOX
    # Qt maakt van een frameloos venster een WS_POPUP; daarvoor toont Windows
    # 11 geen snap-popup (gemeten) — terug naar een gewoon (overlapped) venster.
    stijl &= ~_WS_POPUP
    user32.SetWindowLongPtrW(hwnd, _GWL_STYLE, stijl)

    # Bewust géén DwmExtendFrameIntoClientArea (vaak gebruikt om de schaduw
    # op Windows 10 te houden): gemeten dat Windows 11 dan de snap-popup op
    # de maximaliseerknop niet meer toont. Op Windows 11 blijven schaduw en
    # afgeronde hoeken ook zonder, dankzij WS_THICKFRAME.
    user32.SetWindowPos(
        wintypes.HWND(hwnd), None, 0, 0, 0, 0, _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOZORDER | _SWP_FRAMECHANGED
    )
    return True


def _randdikte(hwnd: int, horizontaal: bool) -> int:
    user32 = ctypes.windll.user32
    try:
        dpi = user32.GetDpiForWindow(wintypes.HWND(hwnd))
        frame = user32.GetSystemMetricsForDpi(_SM_CXSIZEFRAME if horizontaal else _SM_CYSIZEFRAME, dpi)
        padding = user32.GetSystemMetricsForDpi(_SM_CXPADDEDBORDER, dpi)
    except AttributeError:  # Windows ouder dan 10 (1607)
        frame = user32.GetSystemMetrics(_SM_CXSIZEFRAME if horizontaal else _SM_CYSIZEFRAME)
        padding = user32.GetSystemMetrics(_SM_CXPADDEDBORDER)
    return frame + padding


def _autohide_taakbalk_randen(hwnd: int) -> list[int]:
    """De randen (``_ABE_*``) van de monitor van ``hwnd`` waar een
    automatisch verbergende taakbalk zit — meestal leeg."""
    shell32 = ctypes.windll.shell32
    shell32.SHAppBarMessage.restype = ctypes.c_size_t
    shell32.SHAppBarMessage.argtypes = [wintypes.DWORD, ctypes.POINTER(_APPBARDATA)]
    data = _APPBARDATA(cbSize=ctypes.sizeof(_APPBARDATA))
    if not shell32.SHAppBarMessage(_ABM_GETSTATE, ctypes.byref(data)) & _ABS_AUTOHIDE:
        return []
    user32 = ctypes.windll.user32
    user32.MonitorFromWindow.restype = wintypes.HMONITOR
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    monitor = user32.MonitorFromWindow(wintypes.HWND(hwnd), _MONITOR_DEFAULTTONEAREST)
    user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(_MONITORINFO)]
    info = _MONITORINFO(cbSize=ctypes.sizeof(_MONITORINFO))
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return []
    randen = []
    for rand in (_ABE_LEFT, _ABE_TOP, _ABE_RIGHT, _ABE_BOTTOM):
        data = _APPBARDATA(cbSize=ctypes.sizeof(_APPBARDATA), uEdge=rand, rc=info.rcMonitor)
        if shell32.SHAppBarMessage(_ABM_GETAUTOHIDEBAREX, ctypes.byref(data)):
            randen.append(rand)
    return randen


def _punt_in_venster(venster: QWidget, msg) -> tuple[QPoint, bool]:
    """Het punt uit ``lParam`` (fysieke schermpixels) in logische
    coördinaten binnen ``venster``, en of dat de echte muispositie is.

    Bewust niet ``QCursor.pos()``: Windows stuurt ``WM_NCHITTEST`` ook voor
    andere punten dan de muis (o.a. om te bepalen waar de maximaliseerknop
    zit voor de snap-popup) — met de muispositie leek het hele venster dan
    "maximaliseerknop" en verscheen de popup nooit."""
    sx = ctypes.c_short(msg.lParam & 0xFFFF).value
    sy = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(msg.hWnd, ctypes.byref(rect))
    dpr = venster.devicePixelRatioF() or 1.0
    punt = QPoint(int((sx - rect.left) / dpr), int((sy - rect.top) / dpr))
    muis = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(muis))
    return punt, (muis.x, muis.y) == (sx, sy)


def _bevat(venster: QWidget, widget: QWidget | None, punt: QPoint) -> bool:
    return widget is not None and widget.isVisible() and widget.rect().contains(widget.mapFrom(venster, punt))


def _is_knop(widget: QWidget | None, titelbalk: QWidget) -> bool:
    while widget is not None and widget is not titelbalk:
        if isinstance(widget, (QAbstractButton, VensterKnop)) and widget.isEnabled():
            return True
        widget = widget.parentWidget()
    return False


def verwerk_native_event(
    venster: QWidget, titelbalk: QWidget | None, max_knop: VensterKnop | None, event_type, message
):
    """Voor ``nativeEvent`` van het venster: geeft ``(True, resultaat)`` terug
    als het bericht hier is afgehandeld, anders ``None``."""
    if event_type != b"windows_generic_MSG":
        return None
    msg = wintypes.MSG.from_address(int(message))

    if msg.message == _WM_NCCALCSIZE:
        if venster.isMaximized() and not venster.isFullScreen():
            rect = wintypes.RECT.from_address(msg.lParam)
            dx = _randdikte(msg.hWnd, True)
            dy = _randdikte(msg.hWnd, False)
            rect.left += dx
            rect.right -= dx
            rect.top += dy
            rect.bottom -= dy
            for rand in _autohide_taakbalk_randen(msg.hWnd):
                if rand == _ABE_LEFT:
                    rect.left += _AUTOHIDE_RUIMTE
                elif rand == _ABE_TOP:
                    rect.top += _AUTOHIDE_RUIMTE
                elif rand == _ABE_RIGHT:
                    rect.right -= _AUTOHIDE_RUIMTE
                else:
                    rect.bottom -= _AUTOHIDE_RUIMTE
        return True, 0

    if max_knop is not None:
        if msg.message == _WM_NCMOUSEMOVE:
            if msg.wParam == _HTMAXBUTTON:
                max_knop.zet_native_toestand(True, max_knop.is_native_ingedrukt())
                return None  # Windows' eigen afhandeling start de snap-popup
            max_knop.zet_native_toestand(False, False)
            return None
        if msg.message == _WM_NCMOUSELEAVE:
            max_knop.zet_native_toestand(False, False)
            return None
        if msg.message in (_WM_NCLBUTTONDOWN, _WM_NCLBUTTONDBLCLK) and msg.wParam == _HTMAXBUTTON:
            max_knop.zet_native_toestand(True, True)
            return True, 0
        if msg.message == _WM_NCLBUTTONUP and msg.wParam == _HTMAXBUTTON:
            was_ingedrukt = max_knop.is_native_ingedrukt()
            max_knop.zet_native_toestand(True, False)
            if was_ingedrukt:
                max_knop.clicked.emit()
            return True, 0

    if msg.message == _WM_NCHITTEST:
        punt, is_muis = _punt_in_venster(venster, msg)
        x, y = punt.x(), punt.y()

        if not venster.isMaximized() and not venster.isFullScreen():
            r = _RESIZE_RAND
            links, rechts = x < r, x >= venster.width() - r
            boven, onder = y < r, y >= venster.height() - r
            if boven and links:
                return True, _HTTOPLEFT
            if boven and rechts:
                return True, _HTTOPRIGHT
            if onder and links:
                return True, _HTBOTTOMLEFT
            if onder and rechts:
                return True, _HTBOTTOMRIGHT
            if links:
                return True, _HTLEFT
            if rechts:
                return True, _HTRIGHT
            if boven:
                return True, _HTTOP
            if onder:
                return True, _HTBOTTOM

        if _bevat(venster, max_knop, punt):
            return True, _HTMAXBUTTON
        if max_knop is not None and is_muis:
            # Muis is van de knop af zonder niet-client-beweging (bijv. naar
            # de sluitknop ernaast): hover hier al opheffen.
            max_knop.zet_native_toestand(False, False)

        if titelbalk is not None and titelbalk.isVisible():
            lokaal = titelbalk.mapFrom(venster, punt)
            if titelbalk.rect().contains(lokaal) and not _is_knop(titelbalk.childAt(lokaal), titelbalk):
                return True, _HTCAPTION
        return None

    return None
