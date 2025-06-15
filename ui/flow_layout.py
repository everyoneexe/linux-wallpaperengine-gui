"""
FlowLayout - Otomatik sarmalayan layout
QGridLayout'un aksine wallpaper'ları soldan sağa düzgün sıralar
"""

from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtWidgets import QLayout, QLayoutItem, QSizePolicy


class FlowLayout(QLayout):
    """
    Otomatik sarmalayan layout sınıfı.
    Wallpaper'ları soldan sağa düzgün sıralar, boşluk bırakmaz.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._item_list = []
        self._spacing = 10
        
    def addItem(self, item: QLayoutItem) -> None:
        """Layout'a item ekler."""
        self._item_list.append(item)
        
    def count(self) -> int:
        """Item sayısını döner."""
        return len(self._item_list)
        
    def itemAt(self, index: int) -> QLayoutItem:
        """Belirtilen indexteki item'ı döner."""
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None
        
    def takeAt(self, index: int) -> QLayoutItem:
        """Belirtilen indexteki item'ı çıkarır."""
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None
        
    def expandingDirections(self) -> Qt.Orientations:
        """Genişleme yönlerini döner."""
        return Qt.Orientations(Qt.Orientation(0))
        
    def hasHeightForWidth(self) -> bool:
        """Genişliğe göre yükseklik hesaplaması yapılıp yapılmayacağını döner."""
        return True
        
    def heightForWidth(self, width: int) -> int:
        """Belirtilen genişlik için gerekli yüksekliği hesaplar."""
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height
        
    def setGeometry(self, rect: QRect) -> None:
        """Layout geometrisini ayarlar."""
        super().setGeometry(rect)
        self._do_layout(rect, False)
        
    def sizeHint(self) -> QSize:
        """Önerilen boyutu döner."""
        return self.minimumSize()
        
    def minimumSize(self) -> QSize:
        """Minimum boyutu döner."""
        size = QSize()
        
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
            
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), 
                     margins.top() + margins.bottom())
        return size
        
    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        """Layout hesaplamasını yapar."""
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(margins.left(), margins.top(),
                                     -margins.right(), -margins.bottom())
        
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        
        for item in self._item_list:
            widget = item.widget()
            if not widget or not widget.isVisible():
                continue
                
            space_x = self._spacing
            space_y = self._spacing
            
            next_x = x + item.sizeHint().width() + space_x
            
            # Satır sonu kontrolü
            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
                
            if not test_only:
                item.setGeometry(QRect(x, y, item.sizeHint().width(), 
                                     item.sizeHint().height()))
                
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
            
        return y + line_height - rect.y() + margins.bottom()
        
    def setSpacing(self, spacing: int) -> None:
        """Spacing'i ayarlar."""
        self._spacing = spacing
        
    def spacing(self) -> int:
        """Spacing'i döner."""
        return self._spacing
        
    def clear(self) -> None:
        """Tüm item'ları temizler."""
        while self._item_list:
            item = self._item_list.pop()
            if item.widget():
                item.widget().setParent(None)