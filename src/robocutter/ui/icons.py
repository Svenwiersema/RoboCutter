"""Iconen voor de RoboCutter-UI: dikke, afgeronde lijnstijl (Phosphor Bold-
geest, zie ``design/chapters/11-ux-ui.md``).

Phosphor Icons zelf kon niet als lettertype/CSS worden ingeladen (geen Qt-
resource beschikbaar), dus dezelfde paden als in de goedgekeurde HTML-
conceptmockup zijn hier hertekend als losse SVG-fragmenten en worden runtime
naar de juiste thema-/statuskleur gerenderd.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_STROKE = 'fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"'

_ICONS: dict[str, str] = {
    "robot": f'''
        <path d="M12 3v2.5M7 8h10a2 2 0 012 2v6a3 3 0 01-3 3H8a3 3 0 01-3-3v-6a2 2 0 012-2z" {_STROKE}/>
        <circle cx="9.5" cy="12.5" r="1.15" fill="currentColor" stroke="none"/>
        <circle cx="14.5" cy="12.5" r="1.15" fill="currentColor" stroke="none"/>
        <path d="M9 16.2h6" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
    ''',
    "house": f'<path d="M3.5 11.5L12 4l8.5 7.5M5.5 10v8.2a1 1 0 001 1h4.2v-5.6h2.6v5.6H17.5a1 1 0 001-1V10" {_STROKE}/>',
    "layers": f'''
        <path d="M12 3.5l8 4.3-8 4.3-8-4.3 8-4.3z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/>
        <path d="M4 12.2l8 4.3 8-4.3M4 16l8 4.3L20 16" {_STROKE}/>
    ''',
    "recycle": f'''
        <path d="M4.3 12A7.7 7.7 0 0116.8 6.2M19.7 12a7.7 7.7 0 01-12.5 5.8" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
        <path d="M13.8 3.6l3 2.6-3 2.6M10.2 20.4l-3-2.6 3-2.6" {_STROKE}/>
    ''',
    "cube": f'''
        <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/>
        <path d="M4 7.5L12 12l8-4.5M12 12v9" {_STROKE}/>
    ''',
    "folder": '<path d="M3.5 6.8a1.3 1.3 0 011.3-1.3H9l2 2.1h8.2a1.3 1.3 0 011.3 1.3v8.4a1.3 1.3 0 01-1.3 1.3H4.8a1.3 1.3 0 01-1.3-1.3V6.8z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/>',
    "calendar": '''
        <rect x="3.5" y="5.2" width="17" height="15.3" rx="2.2" fill="none" stroke="currentColor" stroke-width="1.9"/>
        <path d="M3.5 9.8h17M8 3.2v3.4M16 3.2v3.4" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
    ''',
    "warning": '''
        <path d="M12 3.6l9.2 15.9a1 1 0 01-.87 1.5H3.67a1 1 0 01-.87-1.5L12 3.6z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/>
        <path d="M12 10v4.2" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
        <circle cx="12" cy="17.1" r="1.1" fill="currentColor" stroke="none"/>
    ''',
    "search": '''
        <circle cx="10.5" cy="10.5" r="6.3" fill="none" stroke="currentColor" stroke-width="1.9"/>
        <path d="M15.2 15.2L20 20" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
    ''',
    "plus": '<path d="M12 4.5v15M4.5 12h15" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"/>',
    "chevron-down": '<path d="M5.5 8.5l6.5 6.5 6.5-6.5" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>',
    "chevron-up": '<path d="M5.5 15.5l6.5-6.5 6.5 6.5" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>',
    "kebab": '''
        <circle cx="12" cy="5.5" r="1.5" fill="currentColor"/>
        <circle cx="12" cy="12" r="1.5" fill="currentColor"/>
        <circle cx="12" cy="18.5" r="1.5" fill="currentColor"/>
    ''',
    "moon": '<path d="M20 14.2A8.4 8.4 0 019.8 4a8.4 8.4 0 1010.2 10.2z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/>',
    "sun": '''
        <circle cx="12" cy="12" r="4.3" fill="none" stroke="currentColor" stroke-width="1.9"/>
        <path d="M12 2.8v2.6M12 18.6v2.6M4.2 12H1.6M22.4 12h-2.6M5.6 5.6l1.9 1.9M16.5 16.5l1.9 1.9M18.4 5.6l-1.9 1.9M7.5 16.5l-1.9 1.9" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
    ''',
    "archive": '''
        <rect x="3.5" y="4.5" width="17" height="4.2" rx="1.2" fill="none" stroke="currentColor" stroke-width="1.9"/>
        <path d="M4.7 8.7v9.1a1.6 1.6 0 001.6 1.6h11.4a1.6 1.6 0 001.6-1.6V8.7M9.8 13h4.4" {stroke}/>
    '''.replace("{stroke}", _STROKE),
    "upload": '''
        <path d="M12 15.5V4.8M8 8.6l4-4 4 4" {stroke}/>
        <path d="M4.5 15v3.2a1.8 1.8 0 001.8 1.8h11.4a1.8 1.8 0 001.8-1.8V15" {stroke}/>
    '''.replace("{stroke}", _STROKE),
    "download": '''
        <path d="M12 4.8v10.7M8 12.6l4 4 4-4" {stroke}/>
        <path d="M4.5 15v3.2a1.8 1.8 0 001.8 1.8h11.4a1.8 1.8 0 001.8-1.8V15" {stroke}/>
    '''.replace("{stroke}", _STROKE),
    "bar": '<rect x="3" y="10" width="18" height="4.2" rx="1.3" fill="none" stroke="currentColor" stroke-width="1.9"/>',
    "grain": '''
        <path d="M4 8.5c2-2 4-2 6 0s4 2 6 0 4-2 4 0M4 15.5c2-2 4-2 6 0s4 2 6 0 4-2 4 0"
              fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
    ''',
    "pencil": '<path d="M14.3 4.8l4.9 4.9M4 20l1-4.6L16.6 3.8a1.7 1.7 0 012.4 0l1.2 1.2a1.7 1.7 0 010 2.4L8.6 19l-4.6 1z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    "trash": '''
        <path d="M4.5 7h15M9.5 7V5.2a1.4 1.4 0 011.4-1.4h2.2a1.4 1.4 0 011.4 1.4V7M6.8 7l.8 12a1.8 1.8 0 001.8 1.7h5.2a1.8 1.8 0 001.8-1.7l.8-12" {stroke}/>
        <path d="M10.3 11v6M13.7 11v6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
    '''.replace("{stroke}", _STROKE.replace("1.9", "1.8")),
    "check": '<path d="M5 12.5l4.5 4.5L19 7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"/>',
    "sliders": '''
        <path d="M3.5 7h9M18.5 7h2M3.5 17h2M9.5 17h11" {stroke}/>
        <circle cx="14.5" cy="7" r="2.3" fill="none" stroke="currentColor" stroke-width="1.9"/>
        <circle cx="6.5" cy="17" r="2.3" fill="none" stroke="currentColor" stroke-width="1.9"/>
    '''.replace("{stroke}", _STROKE),
    "user": '<path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 11a4 4 0 100-8 4 4 0 000 8z" {stroke}/>'.replace("{stroke}", _STROKE),
    "envelope": '''
        <path d="M4 6h16v12H4z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/>
        <path d="M4 7l8 6 8-6" {stroke}/>
    '''.replace("{stroke}", _STROKE),
    "tag": '''
        <path d="M12.6 3.5H6a2.5 2.5 0 00-2.5 2.5v6.6c0 .5.2 1 .55 1.35l8.4 8.4a1.9 1.9 0 002.7 0l6.6-6.6a1.9 1.9 0 000-2.7l-8.4-8.4a1.9 1.9 0 00-1.35-.55z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/>
        <circle cx="8.3" cy="8.3" r="1.3" fill="currentColor" stroke="none"/>
    ''',
    "document": '''
        <path d="M6.5 3.5h8l4 4v13a1 1 0 01-1 1h-11a1 1 0 01-1-1v-16a1 1 0 011-1z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/>
        <path d="M14.5 3.5V8h4M8.5 13h7M8.5 16.5h7" {stroke}/>
    '''.replace("{stroke}", _STROKE),
    "list": '<path d="M4 6h16M4 12h16M4 18h10" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>',
}


def _render(svg: str, size: int, color: str) -> QPixmap:
    document = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{svg}</svg>'
    document = document.replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(document.encode("utf-8")))
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def icon_pixmap(name: str, color: str, size: int = 18) -> QPixmap:
    return _render(_ICONS[name], size, color)


def icon(name: str, color: str, size: int = 18) -> QIcon:
    return QIcon(icon_pixmap(name, color, size))
