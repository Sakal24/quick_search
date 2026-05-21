from qgis.core import (
    Qgis, QgsMapLayerProxyModel, QgsFeatureRequest,
    QgsProject, QgsCoordinateTransform,
)
from PyQt5.QtWidgets import (
    QVBoxLayout, QDialog, QPushButton, QComboBox, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QGroupBox, QHBoxLayout, QWidget,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.utils import iface
from qgis.PyQt.QtCore import QSettings
from PyQt5.QtGui import QIcon
import os


TRANSLATIONS = {
    'en': {
        "Пошук об'єктів": "Search objects",
        "Виберіть шар": "Select layer",
        "Фільтр": "Filter",
        "Пошук": "Search",
        "Шар не вибрано.": "No layer selected.",
        "Увага!": "Warning!",
        "Об'єкти не знайдено.": "No objects found.",
        "Знайдено": "Found",
        "об'єктів": "objects",
        "Обраний об'єкт": "Selected object",
        "Додатковий пошук": "Additional search",
        "Додати фільтр": "Add filter",
        "Прибрати фільтр": "Remove filter",
    }
}

_locale = None

def tr(text):
    global _locale
    if _locale is None:
        locale_value = QSettings().value('locale/userLocale')
        _locale = locale_value[0:2] if locale_value else 'en'
    return TRANSLATIONS.get(_locale, {}).get(text, text)


MAX_FILTERS = 5
MIN_FILTERS = 2


class FeatureListItemWidget(QWidget):
    def __init__(self, feature, fields, edit_callback, double_click_callback):
        super().__init__()
        self.feature = feature
        self.double_click_callback = double_click_callback

        icon_path = os.path.join(os.path.dirname(__file__), "icons", "info.png")

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)

        parts = [str(feature[f] or '') for f in fields]
        layout.addWidget(QLabel(", ".join(parts)))

        edit_button = QPushButton()
        edit_button.setIcon(QIcon(icon_path))
        edit_button.setFixedSize(17, 17)
        edit_button.clicked.connect(lambda: edit_callback(self.feature))
        layout.addWidget(edit_button)

        self.setLayout(layout)

    def mouseDoubleClickEvent(self, event):
        if self.double_click_callback:
            self.double_click_callback(self.feature)


class SearchFeaturesDialog(QDialog):
    def __init__(self, parent=None, is_additional=False):
        super().__init__(parent)
        self.setWindowTitle(tr("Пошук об'єктів"))
        self.filters = []  # list of (groupbox, combo, text_input)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        self.setMinimumWidth(200)
        self.setMaximumWidth(800)

        layer_groupbox = QGroupBox(tr("Виберіть шар"))
        layer_layout = QVBoxLayout(layer_groupbox)
        layer_layout.setContentsMargins(4, 8, 4, 4)
        self.layer_combo = QgsMapLayerComboBox(self)
        self.layer_combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        layer_layout.addWidget(self.layer_combo)
        layout.addWidget(layer_groupbox)

        # Контейнер для динамічних фільтрів
        self._filters_container = QWidget()
        self._filters_layout = QVBoxLayout(self._filters_container)
        self._filters_layout.setContentsMargins(0, 0, 0, 0)
        self._filters_layout.setSpacing(4)
        layout.addWidget(self._filters_container)

        for _ in range(MIN_FILTERS):
            self._add_filter()

        # Кнопки керування фільтрами
        filter_btn_layout = QHBoxLayout()
        filter_btn_layout.addStretch()
        self.add_filter_btn = QPushButton(tr("Додати фільтр"))
        self.add_filter_btn.clicked.connect(self._add_filter)
        filter_btn_layout.addWidget(self.add_filter_btn)
        self.remove_filter_btn = QPushButton(tr("Прибрати фільтр"))
        self.remove_filter_btn.clicked.connect(self._remove_filter)
        filter_btn_layout.addWidget(self.remove_filter_btn)
        layout.addLayout(filter_btn_layout)

        # Кнопки пошуку і додаткової панелі
        button_layout = QHBoxLayout()
        self.search_button = QPushButton(tr("Пошук"))
        self.search_button.setDefault(True)
        self.search_button.clicked.connect(self.search_features)
        button_layout.addWidget(self.search_button)

        self.open_additional_search_button = QPushButton("+")
        self.open_additional_search_button.setFixedSize(20, 20)
        button_layout.addWidget(self.open_additional_search_button)
        layout.addLayout(button_layout)

        self.result_count_label = QLabel(self)
        layout.addWidget(self.result_count_label)

        self.result_list = QListWidget(self)
        layout.addWidget(self.result_list)

        self.selected_object_label = QLabel(self)
        layout.addWidget(self.selected_object_label)

        self.layer_combo.currentIndexChanged.connect(self.update_field_combos)

        self.set_current_layer()
        self._update_filter_buttons()

        if is_additional:
            self.open_additional_search_button.setVisible(False)

    def _add_filter(self):
        if len(self.filters) >= MAX_FILTERS:
            return
        n = len(self.filters) + 1
        groupbox = QGroupBox(f"{tr('Фільтр')} {n}")
        col = QVBoxLayout(groupbox)
        col.setContentsMargins(4, 8, 4, 4)
        combo = QComboBox(self)
        col.addWidget(combo)
        text_input = QLineEdit(self)
        text_input.returnPressed.connect(self.search_features)
        col.addWidget(text_input)
        self._filters_layout.addWidget(groupbox)

        layer = self.layer_combo.currentLayer()
        if layer:
            for field in layer.fields():
                combo.addItem(field.displayName(), field)

        self.filters.append((groupbox, combo, text_input))
        if hasattr(self, 'add_filter_btn'):
            self._update_filter_buttons()

    def _remove_filter(self):
        if len(self.filters) <= MIN_FILTERS:
            return
        groupbox, combo, text_input = self.filters.pop()
        self._filters_layout.removeWidget(groupbox)
        groupbox.deleteLater()
        self._update_filter_buttons()

    def _update_filter_buttons(self):
        self.add_filter_btn.setEnabled(len(self.filters) < MAX_FILTERS)
        self.remove_filter_btn.setEnabled(len(self.filters) > MIN_FILTERS)

    def set_current_layer(self):
        current_layer = iface.activeLayer()
        if current_layer:
            self.layer_combo.setLayer(current_layer)
            self.update_field_combos()

    def update_field_combos(self):
        layer = self.layer_combo.currentLayer()
        for _, combo, _ in self.filters:
            combo.clear()
            if layer:
                for field in layer.fields():
                    combo.addItem(field.displayName(), field)

    def search_features(self):
        layer = self.layer_combo.currentLayer()
        if not layer:
            iface.messageBar().pushMessage(tr('Увага!'), tr("Шар не вибрано."), level=Qgis.Warning, duration=5)
            return

        self.result_list.clear()
        self.result_count_label.clear()
        self.selected_object_label.clear()

        active_fields = [combo.currentData().name() for _, combo, _ in self.filters]
        conditions = []
        for i, (_, combo, text_input) in enumerate(self.filters):
            field = combo.currentData().name()
            text = text_input.text().lower().replace("'", "''")
            if i == 0 or text:
                conditions.append(f'"{field}" ILIKE \'%{text}%\'')

        features = list(layer.getFeatures(
            QgsFeatureRequest().setFilterExpression(' AND '.join(conditions))
        ))

        if not features:
            iface.messageBar().pushMessage(tr('Увага!'), tr("Об'єкти не знайдено."), level=Qgis.Warning, duration=5)
            return

        count_text = tr("об'єктів")
        self.result_count_label.setText(f"{tr('Знайдено')}: {len(features)} {count_text}")

        features.sort(key=lambda x: tuple(x[f] or '' for f in active_fields))

        for feature in features:
            item_widget = FeatureListItemWidget(
                feature, active_fields,
                self.edit_feature, self.show_feature_on_map,
            )
            list_item = QListWidgetItem(self.result_list)
            list_item.setSizeHint(item_widget.sizeHint())
            self.result_list.addItem(list_item)
            self.result_list.setItemWidget(list_item, item_widget)

    def edit_feature(self, feature):
        layer = self.layer_combo.currentLayer()
        if layer:
            iface.openFeatureForm(layer, feature, showModal=False)

    def show_feature_on_map(self, feature):
        layer = self.layer_combo.currentLayer()
        if layer:
            layer.removeSelection()
            layer.selectByIds([feature.id()])

            project_crs = QgsProject.instance().crs()
            layer_crs = layer.crs()
            centroid = feature.geometry().centroid().asPoint()
            if layer_crs != project_crs:
                transform = QgsCoordinateTransform(layer_crs, project_crs, QgsProject.instance())
                centroid = transform.transform(centroid)

            canvas = iface.mapCanvas()
            canvas.setCenter(centroid)
            canvas.zoomScale(1500)

        fields = [combo.currentData().name() for _, combo, _ in self.filters]
        parts = [str(feature.attribute(f) or '') for f in fields]
        selected_text = tr("Обраний об'єкт")
        self.selected_object_label.setText(f"{selected_text}: {', '.join(parts)}")
