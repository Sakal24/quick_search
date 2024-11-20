from qgis.core import QgsFeatureRequest, QgsPointXY, QgsExpression, QgsMapLayerProxyModel
from PyQt5.QtWidgets import QVBoxLayout, QDialog, QPushButton, QComboBox, QLineEdit, QListWidget, QListWidgetItem, QLabel, QGroupBox, QSizePolicy
from qgis.gui import QgsMapLayerComboBox
from qgis.utils import iface
from PyQt5.QtCore import QCoreApplication  # Імпорт QCoreApplication


class CustomListWidgetItem(QListWidgetItem):
    def __init__(self, feature, selected_field1, selected_field2):
        super(CustomListWidgetItem, self).__init__()

        self.feature = feature
        self.selected_field1 = selected_field1
        self.selected_field2 = selected_field2

        # Підписати об'єкт у QListWidget
        self.setText(f"{feature.attribute(selected_field1)}, {feature.attribute(selected_field2)}")

class SearchFeaturesDialog(QDialog):
    def __init__(self, parent=None):
        super(SearchFeaturesDialog, self).__init__(parent)

        self.setWindowTitle(QCoreApplication.translate("SearchFeaturesDialog", "Пошук об'єктів"))

        layout = QVBoxLayout(self)

        self.setMinimumWidth(200)
        self.setMaximumWidth(800)

        # Вибір шару
        layer_groupbox = QGroupBox(QCoreApplication.translate("SearchFeaturesDialog", "Виберіть шар"))
        layer_layout = QVBoxLayout(layer_groupbox)
        self.layer_combo = QgsMapLayerComboBox(self)
        self.layer_combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        layer_layout.addWidget(self.layer_combo)
        layout.addWidget(layer_groupbox)

        # Фільтр 1
        filter1_groupbox = QGroupBox(QCoreApplication.translate("SearchFeaturesDialog", "Фільтр 1"))
        filter1_layout = QVBoxLayout(filter1_groupbox)
        self.field1_combo = QComboBox(self)
        filter1_layout.addWidget(self.field1_combo)
        self.search_value1_input = QLineEdit(self)
        filter1_layout.addWidget(self.search_value1_input)
        layout.addWidget(filter1_groupbox)

        # Фільтр 2
        filter2_groupbox = QGroupBox(QCoreApplication.translate("SearchFeaturesDialog", "Фільтр 2"))
        filter2_layout = QVBoxLayout(filter2_groupbox)
        self.field2_combo = QComboBox(self)
        filter2_layout.addWidget(self.field2_combo)
        self.search_value2_input = QLineEdit(self)
        filter2_layout.addWidget(self.search_value2_input)
        layout.addWidget(filter2_groupbox)

        self.search_button = QPushButton(QCoreApplication.translate("SearchFeaturesDialog", "Пошук"))
        self.search_button.setDefault(True)
        self.search_button.clicked.connect(self.search_features)
        layout.addWidget(self.search_button)

        # Додано віджет QListWidget для відображення результатів
        self.result_list = QListWidget(self)
        layout.addWidget(self.result_list)

        # Додано віджет QLabel для відображення інформації про вибраний об'єкт
        self.selected_object_label = QLabel(self)
        layout.addWidget(self.selected_object_label)

        # Підключення сигналу для обробки подвійного кліку на об'єкт в QListWidget
        self.result_list.itemDoubleClicked.connect(self.show_feature_on_map)

        # Підключення сигналу для оновлення поля вибору при зміні поточного шару
        self.layer_combo.currentIndexChanged.connect(self.update_field_combos)

        # Додаємо обробник натискання клавіші Enter для обох полів введення
        self.search_value1_input.returnPressed.connect(self.search_features)
        self.search_value2_input.returnPressed.connect(self.search_features)

        # Вибір поточного шару при відкритті плагіна
        self.set_current_layer()

    def set_current_layer(self):
        # Отримання поточного активного шару
        current_layer = iface.activeLayer()
        if current_layer:
            # Встановлення поточного шару в QgsMapLayerComboBox
            self.layer_combo.setLayer(current_layer)
            # Оновлення полів після вибору шару
            self.update_field_combos()
        
    def update_field_combos(self):
        # Отримання поточного вибраного шару
        layer = self.layer_combo.currentLayer()

        # Очищення полів вибору при зміні шару
        self.field1_combo.clear()
        self.field2_combo.clear()

        # Заповнення полів вибору новими полями, якщо шар вибрано
        if layer:
            fields = layer.fields()
            for field in fields:
                self.field1_combo.addItem(field.displayName(), field)
                self.field2_combo.addItem(field.displayName(), field)

    def search_features(self):
        # Отримання поточного вибраного шару з QgsMapLayerComboBox
        layer = self.layer_combo.currentLayer()
        if not layer:
            print(QCoreApplication.translate("SearchFeaturesDialog", "Шар не вибрано."))
            return

        # Очищення вмісту QListWidget перед новим пошуком
        self.result_list.clear()
    
        # Отримання поточно вибраних полів з QComboBox
        selected_field1 = self.field1_combo.currentData().name()
        selected_field1_alias = self.field1_combo.currentText()
        selected_field2 = self.field2_combo.currentData().name()
        selected_field2_alias = self.field2_combo.currentText()
    
        # Перетворення тексту фільтрів та значень полів до нижнього регістру
        search_text1 = self.search_value1_input.text().lower()
        search_text2 = self.search_value2_input.text().lower()
    
        print(f"Пошук за полями: {selected_field1}, {selected_field2}")
        print(f"Тексти фільтрів: {search_text1}, {search_text2}")
    
        # Побудова запиту на об'єкти з вказаними умовами
        if search_text2:
            expression_str = f'"{selected_field1}" ILIKE \'%{search_text1}%\' AND "{selected_field2}" ILIKE \'%{search_text2}%\''
        else:
            expression_str = f'"{selected_field1}" ILIKE \'%{search_text1}%\''
    
        print(f"Пошуковий запит: {expression_str}")
        
        # Вибірка об'єктів, які відповідають умовам
        features = [f for f in layer.getFeatures(QgsFeatureRequest().setFilterExpression(expression_str))]
    
        # Якщо об'єкти не знайдено, виводимо повідомлення і не додаємо нічого до списку
        if not features:
            print(QCoreApplication.translate("SearchFeaturesDialog", "Об'єкти не знайдено."))
            return
    
        print(f"Знайдено об'єктів: {len(features)}")
    
        # Сортування об'єктів спочатку за полем selected_field1, а потім за selected_field2
        features_sorted = sorted(features, key=lambda x: (x[selected_field1], x[selected_field2]))
    
        # Додавання знайдених об'єктів до QListWidget з підписами
        for feature in features_sorted:
            custom_item = CustomListWidgetItem(feature, selected_field1_alias, selected_field2_alias)
            self.result_list.addItem(custom_item)

    def show_feature_on_map(self, item):
        # Отримання об'єкта з віджету
        feature = item.feature

        # Встановлення об'єкта як обраного на карті
        layer = self.layer_combo.currentLayer()
        if layer:
            layer.removeSelection()
            layer.selectByIds([feature.id()])

            # Центрування карти на обраному об'єкті
            map_canvas = iface.mapCanvas()
            map_canvas.setCenter(QgsPointXY(feature.geometry().centroid().asPoint()))
            map_canvas.zoomScale(1500)

        # Відображення інформації про вибраний об'єкт у QLabel
        selected_field1 = self.field1_combo.currentText()
        selected_field2 = self.field2_combo.currentText()
        label_text = f"Вибраний об'єкт: {feature.attribute(selected_field1)}, {feature.attribute(selected_field2)}"
        self.selected_object_label.setText(label_text)

