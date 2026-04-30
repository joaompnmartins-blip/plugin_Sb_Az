"""
Povoamentos Sb Az Plugin - Main Plugin Class
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (QAction, QMessageBox, QProgressDialog,
                                  QDialog, QFormLayout, QLabel,
                                  QComboBox, QDialogButtonBox, QFrame,
                                  QCheckBox, QGroupBox, QListWidget,
                                  QListWidgetItem, QVBoxLayout)
from qgis.core import (QgsProject, QgsVectorLayer, QgsProcessing, QgsProperty,
                       QgsField, QgsMessageLog, Qgis, QgsFeature, QgsWkbTypes)
import processing
import os


class LayerConfigDialog(QDialog):
    """Dialog for configuring the input layer and field mappings."""

    _CALC = '__CALCULATE__'

    def __init__(self, parent=None, current_config=None):
        super().__init__(parent)
        self.setWindowTitle('Configuração da Análise de Povoamentos')
        self.setMinimumWidth(500)
        self._setup_ui()
        if current_config:
            self._restore_config(current_config)

    def _setup_ui(self):
        layout = QFormLayout()
        layout.setSpacing(10)
        self.setLayout(layout)

        # --- Main layer ---
        self.layer_combo = QComboBox()
        self._populate_layers()
        layout.addRow('Camada de entrada:', self.layer_combo)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setFrameShadow(QFrame.Sunken)
        layout.addRow(sep1)

        # Crown radius
        self.raio_copa_combo = QComboBox()
        layout.addRow('Campo raio de copa:', self.raio_copa_combo)

        self.pap_label = QLabel('Campo PAP:')
        self.pap_combo = QComboBox()
        layout.addRow(self.pap_label, self.pap_combo)

        self.info_label = QLabel('')
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet('color: #555; font-style: italic;')
        layout.addRow('', self.info_label)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setFrameShadow(QFrame.Sunken)
        layout.addRow(sep2)

        # alt_1m
        self.alt_1m_combo = QComboBox()
        layout.addRow('Campo alt_1m (booleano):', self.alt_1m_combo)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        sep3.setFrameShadow(QFrame.Sunken)
        layout.addRow(sep3)

        # --- Optional affectation section ---
        self.afect_check = QCheckBox(
            'Calcular afectação de infraestruturas (opcional)')
        layout.addRow(self.afect_check)

        self.infra_group = QGroupBox('Camadas de infraestruturas (polígonos)')
        infra_layout = QVBoxLayout()
        infra_layout.setSpacing(4)

        self.infra_list = QListWidget()
        self.infra_list.setMaximumHeight(130)
        self.infra_list.setMinimumHeight(80)
        self._populate_infra_layers()
        infra_layout.addWidget(self.infra_list)

        infra_note = QLabel(
            'Selecione uma ou mais camadas de polígonos. '
            'Camadas não-polígono causarão erro.')
        infra_note.setWordWrap(True)
        infra_note.setStyleSheet('color: #555; font-style: italic;')
        infra_layout.addWidget(infra_note)

        self.infra_group.setLayout(infra_layout)
        self.infra_group.setVisible(False)
        layout.addRow(self.infra_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        # Connections
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        self.raio_copa_combo.currentIndexChanged.connect(self._on_raio_copa_changed)
        self.afect_check.toggled.connect(self.infra_group.setVisible)

        self._on_layer_changed()

    def _populate_layers(self):
        self.layer_combo.clear()
        for layer_id, layer in QgsProject.instance().mapLayers().items():
            if (hasattr(layer, 'geometryType') and
                    layer.geometryType() == QgsWkbTypes.PointGeometry):
                self.layer_combo.addItem(layer.name(), layer_id)

    def _populate_infra_layers(self):
        self.infra_list.clear()
        for layer_id, layer in QgsProject.instance().mapLayers().items():
            if (hasattr(layer, 'geometryType') and
                    layer.geometryType() == QgsWkbTypes.PolygonGeometry):
                item = QListWidgetItem(layer.name())
                item.setData(Qt.UserRole, layer_id)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.infra_list.addItem(item)

    def _on_layer_changed(self):
        layer_id = self.layer_combo.currentData()
        if not layer_id:
            return
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            return

        self.raio_copa_combo.blockSignals(True)
        self.raio_copa_combo.clear()
        self.raio_copa_combo.addItem('— Calcular de PAP (campo não existe) —', self._CALC)
        self.pap_combo.clear()
        self.alt_1m_combo.clear()

        bool_int_fields = []
        numeric_fields = []

        for field in layer.fields():
            ftype = field.type()
            fname = field.name()
            if ftype in (QVariant.Int, QVariant.LongLong, QVariant.Double):
                numeric_fields.append(fname)
            if ftype in (QVariant.Bool, QVariant.Int, QVariant.LongLong):
                bool_int_fields.append(fname)

        for fname in numeric_fields:
            self.raio_copa_combo.addItem(fname, fname)
            self.pap_combo.addItem(fname, fname)

        if bool_int_fields:
            for fname in bool_int_fields:
                self.alt_1m_combo.addItem(fname, fname)
        else:
            for field in layer.fields():
                self.alt_1m_combo.addItem(field.name(), field.name())

        self.raio_copa_combo.blockSignals(False)
        self._on_raio_copa_changed()

    def _on_raio_copa_changed(self):
        needs_calc = self.raio_copa_combo.currentData() == self._CALC
        if needs_calc:
            self.pap_label.setText('Campo PAP:')
            self.info_label.setText(
                'O campo PAP será usado para calcular o raio de copa (campo criado '
                'automaticamente se não existir) e para classificação das árvores.'
            )
        else:
            self.pap_label.setText('Campo PAP (classificação):')
            self.info_label.setText(
                'Os valores de raio de copa existentes serão usados para os buffers. '
                'O campo PAP é ainda necessário para classificação das árvores por classe.'
            )

    def _validate_and_accept(self):
        if self.layer_combo.count() == 0:
            QMessageBox.warning(self, 'Erro',
                'Não foram encontradas camadas de pontos no projecto.')
            return
        if self.pap_combo.count() == 0:
            QMessageBox.warning(self, 'Erro',
                'Não foram encontrados campos numéricos para o campo PAP.')
            return
        if self.alt_1m_combo.count() == 0:
            QMessageBox.warning(self, 'Erro',
                'Não foram encontrados campos para o campo alt_1m.')
            return
        if self.afect_check.isChecked() and not self._get_selected_infra_ids():
            QMessageBox.warning(self, 'Erro',
                'Selecione pelo menos uma camada de infraestruturas, '
                'ou desactive a opção de afectação.')
            return
        self.accept()

    def _get_selected_infra_ids(self):
        selected = []
        for i in range(self.infra_list.count()):
            item = self.infra_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected

    def _restore_config(self, config):
        idx = self.layer_combo.findData(config.get('layer_id'))
        if idx >= 0:
            self.layer_combo.setCurrentIndex(idx)
            self._on_layer_changed()

        if config.get('needs_calculation', True):
            self.raio_copa_combo.setCurrentIndex(0)
        else:
            rc = config.get('raio_copa_field')
            if rc:
                idx = self.raio_copa_combo.findData(rc)
                if idx >= 0:
                    self.raio_copa_combo.setCurrentIndex(idx)

        pap = config.get('pap_field')
        if pap:
            idx = self.pap_combo.findData(pap)
            if idx >= 0:
                self.pap_combo.setCurrentIndex(idx)

        alt = config.get('alt_1m_field')
        if alt:
            idx = self.alt_1m_combo.findData(alt)
            if idx >= 0:
                self.alt_1m_combo.setCurrentIndex(idx)

        # Restore affectation
        calc_afect = config.get('calc_afectacao', False)
        self.afect_check.setChecked(calc_afect)
        self.infra_group.setVisible(calc_afect)

        infra_ids = set(config.get('infra_layer_ids', []))
        for i in range(self.infra_list.count()):
            item = self.infra_list.item(i)
            item.setCheckState(
                Qt.Checked if item.data(Qt.UserRole) in infra_ids else Qt.Unchecked)

    def get_config(self):
        raio_copa_data = self.raio_copa_combo.currentData()
        needs_calc = raio_copa_data == self._CALC
        return {
            'layer_id': self.layer_combo.currentData(),
            'layer_name': self.layer_combo.currentText(),
            'pap_field': self.pap_combo.currentData(),
            'raio_copa_field': 'raio_copa' if needs_calc else raio_copa_data,
            'alt_1m_field': self.alt_1m_combo.currentData(),
            'needs_calculation': needs_calc,
            'calc_afectacao': self.afect_check.isChecked(),
            'infra_layer_ids': self._get_selected_infra_ids(),
        }


class PovoamentosSbAzPlugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr(u'&Povoamentos Sb Az')

        # Runtime configuration (populated by dialog)
        self.layer_id = None
        self.pap_field = 'PAP'
        self.raio_copa_field = 'raio_copa'
        self.alt_1m_field = 'alt_1m'
        self.needs_calculation = True
        self.calc_afectacao = False
        self.infra_layer_ids = []

        # Output layer names
        self.BUFFER_LAYER_NAME = 'LIMITE_COPAS'
        self.CONTINUIDADE_LAYER_NAME = 'LIMITE_CONTINUIDADE'
        self.CLASSES_PAP_LAYER_NAME = 'CLASSES_PAP'

    def tr(self, message):
        return QCoreApplication.translate('PovoamentosSbAz', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True,
                   status_tip=None, whats_this=None, parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.iface.addToolBarIcon(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        if not os.path.exists(icon_path):
            icon_path = ''
        self.add_action(
            icon_path,
            text=self.tr(u'Correr análise de povoamentos'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&PovoamentosSbAz'), action)
            self.iface.removeToolBarIcon(action)

    def log(self, message, level=Qgis.Info):
        QgsMessageLog.logMessage(message, 'Povoamentos Sb Az', level)

    def _show_config_dialog(self):
        """Show the layer/field configuration dialog. Returns True if accepted."""
        current_config = {
            'layer_id': self.layer_id,
            'pap_field': self.pap_field,
            'raio_copa_field': self.raio_copa_field,
            'alt_1m_field': self.alt_1m_field,
            'needs_calculation': self.needs_calculation,
            'calc_afectacao': self.calc_afectacao,
            'infra_layer_ids': self.infra_layer_ids,
        }
        dlg = LayerConfigDialog(self.iface.mainWindow(), current_config)
        if dlg.exec_() != QDialog.Accepted:
            return False
        cfg = dlg.get_config()
        self.layer_id = cfg['layer_id']
        self.pap_field = cfg['pap_field']
        self.raio_copa_field = cfg['raio_copa_field']
        self.alt_1m_field = cfg['alt_1m_field']
        self.needs_calculation = cfg['needs_calculation']
        self.calc_afectacao = cfg['calc_afectacao']
        self.infra_layer_ids = cfg['infra_layer_ids']
        return True

    def run(self):
        """Executar a análise do plugin."""

        if not self._show_config_dialog():
            return

        total_steps = 7 if self.calc_afectacao else 6
        progress = QProgressDialog('A Processar...', 'Cancelar', 0, total_steps,
                                   self.iface.mainWindow())
        progress.setWindowTitle('Análise de Povoamentos')
        progress.setModal(True)
        progress.show()

        try:
            # Step 1
            if self.needs_calculation:
                progress.setLabelText('Passo 1/6: Calcular raio de copa...')
                progress.setValue(1)
                QCoreApplication.processEvents()
                success_count = self.calculate_raio_copa()
                if success_count == 0:
                    raise Exception('Falha a calcular raio de copa')
                self.log(f'Passo 1 completo: {success_count} elementos calculados')
            else:
                progress.setLabelText('Passo 1/6: Raio de copa existente, a saltar cálculo...')
                progress.setValue(1)
                QCoreApplication.processEvents()
                self.log('Passo 1 saltado: campo raio de copa já contém valores')

            if progress.wasCanceled():
                return

            # Step 2
            progress.setLabelText('Passo 2/6: Criar buffers copas...')
            progress.setValue(2)
            QCoreApplication.processEvents()
            buffer_layer = self.create_buffer_layer()
            self.log(f'Passo 2 completo: {buffer_layer.featureCount()} buffers criados')

            if progress.wasCanceled():
                return

            # Step 3
            progress.setLabelText('Passo 3/6: Criar buffer dissolvido de 10m...')
            progress.setValue(3)
            QCoreApplication.processEvents()
            continuidade_layer = self.create_continuidade_layer(buffer_layer)
            self.log(f'Passo 3 completo: {continuidade_layer.featureCount()} elementos')

            if progress.wasCanceled():
                return

            # Step 3.5
            progress.setLabelText('Passo 3.5/6: Separar áreas por tamanho (0.5 ha)...')
            QCoreApplication.processEvents()
            large_areas_layer, small_areas_layer = self.split_by_area_threshold(
                continuidade_layer)
            self.log(f'Áreas separadas: {large_areas_layer.featureCount()} ≥ 0.5 ha, '
                     f'{small_areas_layer.featureCount()} < 0.5 ha')

            if progress.wasCanceled():
                return

            # Step 4
            progress.setLabelText('Passo 4/6: Analisando classes de PAP (áreas ≥ 0.5 ha)...')
            progress.setValue(4)
            QCoreApplication.processEvents()
            classes_pap_layer, source_layer = self.create_classes_pap_layer(
                large_areas_layer)
            self.log(f'Passo 4 completo: {classes_pap_layer.featureCount()} polígonos')

            if progress.wasCanceled():
                return

            # Step 5
            progress.setLabelText('Passo 5/6: Criar camada POVOAMENTO...')
            progress.setValue(5)
            QCoreApplication.processEvents()
            povoamento_layer = self.create_povoamento_layer(classes_pap_layer)
            if povoamento_layer:
                self.log(f'Passo 5 completo: {povoamento_layer.featureCount()} áreas')
            else:
                self.log('Passo 5 completo: Nenhuma área encontrada')

            if progress.wasCanceled():
                return

            # Step 6
            progress.setLabelText('Passo 6/6: Criar camada PEQUENO_NUCLEO...')
            progress.setValue(6)
            QCoreApplication.processEvents()
            pequeno_layer, outros_layer = self.create_pequeno_nucleo_layer(
                small_areas_layer, source_layer)
            if pequeno_layer and pequeno_layer.featureCount() > 0:
                self.log(f'Passo 6 completo: {pequeno_layer.featureCount()} pequenos núcleos')
            else:
                self.log('Passo 6: Nenhum pequeno núcleo encontrado')
            if outros_layer and outros_layer.featureCount() > 0:
                self.log(f'Passo 6: {outros_layer.featureCount()} outros')

            # Step 7 (optional)
            areas_afectadas = None
            sb_az_afectados = None
            if self.calc_afectacao and self.infra_layer_ids:
                progress.setLabelText('Passo 7/7: Calcular afectação de infraestruturas...')
                progress.setValue(7)
                QCoreApplication.processEvents()
                areas_afectadas, sb_az_afectados = self.create_afectacao_layers(
                    povoamento_layer, source_layer)
                if areas_afectadas:
                    self.log(f'Passo 7 completo: {areas_afectadas.featureCount()} '
                             'áreas afectadas')
                else:
                    self.log('Passo 7: Nenhuma área de povoamento afectada')

            progress.setValue(total_steps)

            # Build summary
            layers_created = [self.BUFFER_LAYER_NAME, self.CONTINUIDADE_LAYER_NAME,
                              self.CLASSES_PAP_LAYER_NAME]
            if povoamento_layer:
                layers_created.append('POVOAMENTO')
            if pequeno_layer and pequeno_layer.featureCount() > 0:
                layers_created.append('PEQUENO_NUCLEO')
            if outros_layer and outros_layer.featureCount() > 0:
                layers_created.append('OUTROS')
            if areas_afectadas:
                layers_created.append('INFRAESTRUTURAS_TOTAL')
                layers_created.append('AREAS_AFECTADAS')
            if sb_az_afectados:
                layers_created.append('SB_AZ_AFECTADOS')

            QMessageBox.information(
                self.iface.mainWindow(),
                'Análise Completa',
                f'Criados com sucesso {len(layers_created)} camadas:\n' +
                '\n'.join(f'  • {name}' for name in layers_created)
            )

        except Exception as e:
            QgsMessageLog.logMessage(str(e), 'Povoamentos Sb Az', Qgis.Critical)
            QMessageBox.critical(
                self.iface.mainWindow(), 'Erro',
                f'Ocorreu um erro durante o processamento:\n\n{str(e)}'
            )
        finally:
            progress.close()

    def calculate_raio_copa(self):
        """Step 1: Calculate raio de copa from PAP field, creating the field if absent."""
        layer = QgsProject.instance().mapLayer(self.layer_id)
        if not layer:
            raise Exception('Camada não encontrada no projecto')
        if layer.fields().indexOf(self.pap_field) == -1:
            raise Exception(f"Campo PAP '{self.pap_field}' não encontrado na camada")

        if layer.fields().indexOf(self.raio_copa_field) == -1:
            layer.startEditing()
            rc_field = QgsField(self.raio_copa_field, QVariant.Double)
            rc_field.setLength(10)
            rc_field.setPrecision(4)
            layer.addAttribute(rc_field)
            layer.commitChanges()
            self.log(f"Campo '{self.raio_copa_field}' criado na camada")

        layer.startEditing()
        target_idx = layer.fields().indexOf(self.raio_copa_field)
        success_count = 0

        for feature in layer.getFeatures():
            pap_value = feature[self.pap_field]
            if pap_value is None or pap_value == 0:
                continue
            result = ((pap_value ** 0.6849) * 0.299) / 2
            layer.changeAttributeValue(feature.id(), target_idx, result)
            success_count += 1

        layer.commitChanges()
        layer.triggerRepaint()
        return success_count

    def create_buffer_layer(self):
        """Step 2: Create buffer layer using the raio de copa field."""
        layer = QgsProject.instance().mapLayer(self.layer_id)
        buffer_result = processing.run('native:buffer', {
            'INPUT': layer,
            'DISTANCE': QgsProperty.fromField(self.raio_copa_field),
            'SEGMENTS': 16,
            'END_CAP_STYLE': 0,
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'DISSOLVE': False,
            'OUTPUT': 'memory:'
        })
        buffer_layer = buffer_result['OUTPUT']
        buffer_layer.setName(self.BUFFER_LAYER_NAME)
        QgsProject.instance().addMapLayer(buffer_layer)
        return buffer_layer

    def create_continuidade_layer(self, buffer_layer):
        """Step 3: Create 10m dissolved buffer layer."""
        dissolved_result = processing.run('native:dissolve', {
            'INPUT': buffer_layer, 'FIELD': [], 'OUTPUT': 'memory:'
        })
        buffer_10m_result = processing.run('native:buffer', {
            'INPUT': dissolved_result['OUTPUT'],
            'DISTANCE': 10, 'SEGMENTS': 16,
            'END_CAP_STYLE': 0, 'JOIN_STYLE': 0,
            'MITER_LIMIT': 2, 'DISSOLVE': True, 'OUTPUT': 'memory:'
        })
        singlepart_result = processing.run('native:multiparttosingleparts', {
            'INPUT': buffer_10m_result['OUTPUT'], 'OUTPUT': 'memory:'
        })
        continuidade_layer = singlepart_result['OUTPUT']
        continuidade_layer.setName(self.CONTINUIDADE_LAYER_NAME)

        continuidade_layer.startEditing()
        if continuidade_layer.fields().indexOf('area_ha') == -1:
            field = QgsField('area_ha', QVariant.Double)
            field.setLength(10); field.setPrecision(4)
            continuidade_layer.addAttribute(field)
        continuidade_layer.updateFields()
        area_idx = continuidade_layer.fields().indexOf('area_ha')
        for feature in continuidade_layer.getFeatures():
            geom = feature.geometry()
            if geom:
                continuidade_layer.changeAttributeValue(
                    feature.id(), area_idx, geom.area() / 10000)
        continuidade_layer.commitChanges()
        QgsProject.instance().addMapLayer(continuidade_layer)
        return continuidade_layer

    def split_by_area_threshold(self, continuidade_layer):
        """Step 3.5: Split polygons by 0.5 ha threshold."""
        large_result = processing.run('native:extractbyexpression', {
            'INPUT': continuidade_layer,
            'EXPRESSION': '"area_ha" >= 0.5', 'OUTPUT': 'memory:'
        })
        large_areas_layer = large_result['OUTPUT']
        large_areas_layer.setName('AREAS_GRANDES')

        small_result = processing.run('native:extractbyexpression', {
            'INPUT': continuidade_layer,
            'EXPRESSION': '"area_ha" < 0.5', 'OUTPUT': 'memory:'
        })
        small_areas_layer = small_result['OUTPUT']
        small_areas_layer.setName('AREAS_PEQUENAS')
        return large_areas_layer, small_areas_layer

    def create_classes_pap_layer(self, continuidade_layer):
        """Step 4: Create CLASSES_PAP layer with PAP analysis."""
        layer = QgsProject.instance().mapLayer(self.layer_id)

        final_result = processing.run('native:extractbyexpression', {
            'INPUT': continuidade_layer,
            'EXPRESSION': '"area_ha" > 0.5', 'OUTPUT': 'memory:'
        })
        final_layer = final_result['OUTPUT']
        final_layer.setName(self.CLASSES_PAP_LAYER_NAME)
        final_layer.startEditing()

        pap_classes = [
            ('under_30',   0,   30,          'PAP < 30'),
            ('pap_30_79',  30,  79,          'PAP 30-79'),
            ('pap_80_129', 80,  129,         'PAP 80-129'),
            ('over_129',   130, float('inf'), 'PAP > 129'),
        ]

        for class_name, _, _, _ in pap_classes:
            if final_layer.fields().indexOf(f'n_{class_name}') == -1:
                final_layer.addAttribute(QgsField(f'n_{class_name}', QVariant.Int))
            if final_layer.fields().indexOf(f'avg_{class_name}') == -1:
                f = QgsField(f'avg_{class_name}', QVariant.Double)
                f.setLength(10); f.setPrecision(2)
                final_layer.addAttribute(f)
            if final_layer.fields().indexOf(f'dens_{class_name}') == -1:
                f = QgsField(f'dens_{class_name}', QVariant.Double)
                f.setLength(10); f.setPrecision(4)
                final_layer.addAttribute(f)

        for fname, ftype, length, prec in [
            ('n_total',    QVariant.Int,    10, 0),
            ('dens_total', QVariant.Double, 10, 4),
            ('avg_total',  QVariant.Double, 10, 2),
        ]:
            if final_layer.fields().indexOf(fname) == -1:
                f = QgsField(fname, ftype)
                if ftype == QVariant.Double:
                    f.setLength(length); f.setPrecision(prec)
                final_layer.addAttribute(f)

        for fname, ftype, length in [
            ('pap_class',      QVariant.Int,    0),
            ('Povoamento',     QVariant.String, 3),
            ('Pov_Repescagem', QVariant.String, 3),
        ]:
            if final_layer.fields().indexOf(fname) == -1:
                f = QgsField(fname, ftype)
                if ftype == QVariant.String:
                    f.setLength(length)
                final_layer.addAttribute(f)

        final_layer.updateFields()

        output_fields = {
            'area_ha', 'pap_class', 'Povoamento', 'Pov_Repescagem',
            'n_total', 'dens_total', 'avg_total',
        }
        for class_name, _, _, _ in pap_classes:
            output_fields.update({f'n_{class_name}', f'avg_{class_name}',
                                   f'dens_{class_name}'})

        ids_to_remove = [
            final_layer.fields().indexOf(f.name())
            for f in final_layer.fields()
            if f.name() not in output_fields
        ]
        if ids_to_remove:
            final_layer.deleteAttributes(ids_to_remove)
            final_layer.updateFields()

        fidx = {}
        for class_name, _, _, _ in pap_classes:
            fidx[f'n_{class_name}']    = final_layer.fields().indexOf(f'n_{class_name}')
            fidx[f'avg_{class_name}']  = final_layer.fields().indexOf(f'avg_{class_name}')
            fidx[f'dens_{class_name}'] = final_layer.fields().indexOf(f'dens_{class_name}')
        for name in ('n_total', 'dens_total', 'avg_total', 'pap_class',
                     'Povoamento', 'Pov_Repescagem'):
            fidx[name] = final_layer.fields().indexOf(name)

        class_thresholds = {1: 50, 2: 30, 3: 20, 4: 10}

        for poly_feature in final_layer.getFeatures():
            poly_geom = poly_feature.geometry()
            poly_area = poly_feature['area_ha']
            class_data = {cn: {'count': 0, 'sum_pap': 0} for cn, *_ in pap_classes}
            total_count = 0
            total_sum_pap = 0

            for point_feature in layer.getFeatures():
                alt_val = point_feature[self.alt_1m_field]
                if alt_val is False or alt_val == 0 or alt_val is None:
                    continue
                if not poly_geom.contains(point_feature.geometry()):
                    continue
                pap_value = point_feature[self.pap_field]
                if pap_value is None:
                    continue
                total_count += 1
                total_sum_pap += pap_value
                for class_name, min_val, max_val, _ in pap_classes:
                    if (min_val <= pap_value < max_val or
                            (max_val == float('inf') and pap_value >= min_val)):
                        class_data[class_name]['count'] += 1
                        class_data[class_name]['sum_pap'] += pap_value
                        break

            for class_name, _, _, _ in pap_classes:
                count = class_data[class_name]['count']
                final_layer.changeAttributeValue(
                    poly_feature.id(), fidx[f'n_{class_name}'], count)
                if count > 0:
                    final_layer.changeAttributeValue(
                        poly_feature.id(), fidx[f'avg_{class_name}'],
                        class_data[class_name]['sum_pap'] / count)
                    final_layer.changeAttributeValue(
                        poly_feature.id(), fidx[f'dens_{class_name}'],
                        count / poly_area if poly_area > 0 else 0)
                else:
                    final_layer.changeAttributeValue(
                        poly_feature.id(), fidx[f'avg_{class_name}'], None)
                    final_layer.changeAttributeValue(
                        poly_feature.id(), fidx[f'dens_{class_name}'], 0)

            final_layer.changeAttributeValue(
                poly_feature.id(), fidx['n_total'], total_count)
            if poly_area and poly_area > 0:
                final_layer.changeAttributeValue(
                    poly_feature.id(), fidx['dens_total'], total_count / poly_area)

            if total_count > 0:
                avg_total = total_sum_pap / total_count
                final_layer.changeAttributeValue(
                    poly_feature.id(), fidx['avg_total'], avg_total)
                pap_class = (1 if avg_total < 30 else
                             2 if avg_total < 80 else
                             3 if avg_total < 130 else 4)
                final_layer.changeAttributeValue(
                    poly_feature.id(), fidx['pap_class'], pap_class)
                total_density = total_count / poly_area if poly_area > 0 else 0
                pov_rep = 'Sim' if total_density > class_thresholds.get(pap_class, 0) else 'Não'
                final_layer.changeAttributeValue(
                    poly_feature.id(), fidx['Pov_Repescagem'], pov_rep)
            else:
                final_layer.changeAttributeValue(
                    poly_feature.id(), fidx['avg_total'], None)
                final_layer.changeAttributeValue(
                    poly_feature.id(), fidx['pap_class'], None)
                final_layer.changeAttributeValue(
                    poly_feature.id(), fidx['Pov_Repescagem'], 'Não')

            dens = {cn: class_data[cn]['count'] / poly_area if poly_area > 0 else 0
                    for cn, *_ in pap_classes}
            povoamento_value = (
                'Sim' if (dens['under_30'] > 50 or dens['pap_30_79'] > 30 or
                          dens['pap_80_129'] > 20 or dens['over_129'] > 10)
                else 'Não'
            )
            final_layer.changeAttributeValue(
                poly_feature.id(), fidx['Povoamento'], povoamento_value)

        final_layer.commitChanges()
        QgsProject.instance().addMapLayer(final_layer)
        return final_layer, layer

    def create_povoamento_layer(self, classes_pap_layer):
        """Step 5: Create POVOAMENTO layer."""
        count = sum(
            1 for f in classes_pap_layer.getFeatures()
            if f['Povoamento'] == 'Sim' or f['Pov_Repescagem'] == 'Sim'
        )
        if count == 0:
            return None
        result = processing.run('native:extractbyexpression', {
            'INPUT': classes_pap_layer,
            'EXPRESSION': '"Povoamento" = \'Sim\' OR "Pov_Repescagem" = \'Sim\'',
            'OUTPUT': 'memory:'
        })
        povoamento_layer = result['OUTPUT']
        povoamento_layer.setName('POVOAMENTO')
        QgsProject.instance().addMapLayer(povoamento_layer)
        return povoamento_layer

    def create_pequeno_nucleo_layer(self, small_areas_layer, source_layer):
        """Step 6: Create PEQUENO_NUCLEO and OUTROS layers from small areas (<0.5 ha)."""
        if small_areas_layer.featureCount() == 0:
            return None, None

        temp_layer = QgsVectorLayer(
            f'Polygon?crs={small_areas_layer.crs().authid()}', 'temp', 'memory')
        temp_layer.startEditing()
        for field in small_areas_layer.fields():
            temp_layer.addAttribute(field)
        temp_layer.addAttribute(QgsField('n_total',         QVariant.Int))
        temp_layer.addAttribute(QgsField('dens_total',      QVariant.Double))
        temp_layer.addAttribute(QgsField('avg_PAP',         QVariant.Double))
        temp_layer.addAttribute(QgsField('pap_class',       QVariant.Int))
        temp_layer.addAttribute(QgsField('meets_threshold', QVariant.String))
        temp_layer.updateFields()

        for src_feature in small_areas_layer.getFeatures():
            new_feat = QgsFeature(temp_layer.fields())
            new_feat.setGeometry(src_feature.geometry())
            for field in small_areas_layer.fields():
                new_feat[field.name()] = src_feature[field.name()]
            temp_layer.addFeature(new_feat)
        temp_layer.commitChanges()
        temp_layer.startEditing()

        n_total_idx         = temp_layer.fields().indexOf('n_total')
        dens_total_idx      = temp_layer.fields().indexOf('dens_total')
        avg_pap_idx         = temp_layer.fields().indexOf('avg_PAP')
        pap_class_idx       = temp_layer.fields().indexOf('pap_class')
        meets_threshold_idx = temp_layer.fields().indexOf('meets_threshold')
        class_thresholds    = {1: 50, 2: 30, 3: 20, 4: 10}

        for poly_feature in temp_layer.getFeatures():
            poly_geom = poly_feature.geometry()
            poly_area = poly_feature['area_ha']
            point_count = 0
            sum_pap = 0

            for point_feature in source_layer.getFeatures():
                alt_val = point_feature[self.alt_1m_field]
                if alt_val is False or alt_val == 0 or alt_val is None:
                    continue
                if not poly_geom.contains(point_feature.geometry()):
                    continue
                pap_value = point_feature[self.pap_field]
                if pap_value is not None:
                    point_count += 1
                    sum_pap += pap_value

            temp_layer.changeAttributeValue(poly_feature.id(), n_total_idx, point_count)
            density = (point_count / poly_area) if poly_area and poly_area > 0 else 0
            temp_layer.changeAttributeValue(poly_feature.id(), dens_total_idx, density)

            if point_count > 0:
                avg_pap = sum_pap / point_count
                temp_layer.changeAttributeValue(poly_feature.id(), avg_pap_idx, avg_pap)
                pap_class = (1 if avg_pap < 30 else
                             2 if avg_pap < 80 else
                             3 if avg_pap < 130 else 4)
                temp_layer.changeAttributeValue(poly_feature.id(), pap_class_idx, pap_class)
                meets = 'Sim' if density > class_thresholds.get(pap_class, 0) else 'Não'
                temp_layer.changeAttributeValue(
                    poly_feature.id(), meets_threshold_idx, meets)
            else:
                temp_layer.changeAttributeValue(poly_feature.id(), avg_pap_idx, None)
                temp_layer.changeAttributeValue(poly_feature.id(), pap_class_idx, None)
                temp_layer.changeAttributeValue(
                    poly_feature.id(), meets_threshold_idx, 'Não')

        temp_layer.commitChanges()

        fields_to_keep = {'area_ha', 'n_total', 'dens_total', 'avg_PAP', 'pap_class'}

        def _finalise(raw_layer, layer_name, id_field_name):
            if raw_layer.featureCount() == 0:
                return None
            raw_layer.setName(layer_name)
            raw_layer.startEditing()
            ids_to_remove = [
                raw_layer.fields().indexOf(f.name())
                for f in raw_layer.fields()
                if f.name() not in fields_to_keep
            ]
            if ids_to_remove:
                raw_layer.deleteAttributes(ids_to_remove)
                raw_layer.updateFields()
            raw_layer.addAttribute(QgsField(id_field_name, QVariant.Int))
            raw_layer.updateFields()
            dens_idx = raw_layer.fields().indexOf('dens_total')
            if dens_idx != -1:
                raw_layer.renameAttribute(dens_idx, 'dens_arv')
            id_idx = raw_layer.fields().indexOf(id_field_name)
            for i, feature in enumerate(raw_layer.getFeatures(), start=1):
                raw_layer.changeAttributeValue(feature.id(), id_idx, i)
            raw_layer.commitChanges()
            QgsProject.instance().addMapLayer(raw_layer)
            return raw_layer

        pequeno_result = processing.run('native:extractbyexpression', {
            'INPUT': temp_layer,
            'EXPRESSION': '"meets_threshold" = \'Sim\'', 'OUTPUT': 'memory:'
        })
        outros_result = processing.run('native:extractbyexpression', {
            'INPUT': temp_layer,
            'EXPRESSION': '"meets_threshold" = \'Não\'', 'OUTPUT': 'memory:'
        })
        return (_finalise(pequeno_result['OUTPUT'], 'PEQUENO_NUCLEO', 'n_nucleo'),
                _finalise(outros_result['OUTPUT'], 'OUTROS', 'n_outros'))

    def create_afectacao_layers(self, povoamento_layer, source_layer):
        """Step 7 (optional): Calculate direct affectation of infrastructure."""

        # Validate and collect infrastructure layers
        infra_layers = []
        for layer_id in self.infra_layer_ids:
            layer = QgsProject.instance().mapLayer(layer_id)
            if not layer:
                continue
            if layer.geometryType() != QgsWkbTypes.PolygonGeometry:
                raise Exception(
                    f"A camada '{layer.name()}' não é uma camada de polígonos. "
                    "Apenas polígonos são suportados para infraestruturas.")
            infra_layers.append(layer)

        if not infra_layers:
            return None, None

        # Combine all infrastructure layers into one dissolved polygon
        merge_result = processing.run('native:mergevectorlayers', {
            'LAYERS': infra_layers,
            'CRS': infra_layers[0].crs().authid(),
            'OUTPUT': 'memory:'
        })
        dissolve_result = processing.run('native:dissolve', {
            'INPUT': merge_result['OUTPUT'],
            'FIELD': [], 'OUTPUT': 'memory:'
        })
        infra_total = dissolve_result['OUTPUT']
        infra_total.setName('INFRAESTRUTURAS_TOTAL')
        QgsProject.instance().addMapLayer(infra_total)
        self.log(f'Infraestruturas combinadas: {len(infra_layers)} camada(s)')

        # Intersect POVOAMENTO × infrastructure (only if POVOAMENTO exists)
        areas_afectadas = None
        if povoamento_layer and povoamento_layer.featureCount() > 0:
            intersect_result = processing.run('native:intersection', {
                'INPUT': povoamento_layer,
                'OVERLAY': infra_total,
                'INPUT_FIELDS': [],
                'OVERLAY_FIELDS': [],
                'OVERLAY_FIELDS_PREFIX': '',
                'OUTPUT': 'memory:'
            })
            intersect_layer = intersect_result['OUTPUT']

            if intersect_layer.featureCount() > 0:
                area_result = processing.run('native:fieldcalculator', {
                    'INPUT': intersect_layer,
                    'FIELD_NAME': 'area_ha_afect',
                    'FIELD_TYPE': 0,  # Double
                    'FIELD_LENGTH': 10,
                    'FIELD_PRECISION': 4,
                    'FORMULA': '$area / 10000',
                    'OUTPUT': 'memory:'
                })
                areas_afectadas = area_result['OUTPUT']
                areas_afectadas.setName('AREAS_AFECTADAS')
                QgsProject.instance().addMapLayer(areas_afectadas)
            else:
                self.log('Nenhuma área de povoamento intersecta as infraestruturas')

        # Classify sb_az as 'povoamento' or 'isolados' and find affected trees
        sb_az_afectados = None
        if source_layer:
            # Split trees by whether they're inside POVOAMENTO
            pov_join = processing.run('native:joinattributesbylocation', {
                'INPUT': source_layer,
                'JOIN': povoamento_layer if povoamento_layer else infra_total,
                'JOIN_FIELDS': [],
                'METHOD': 0,
                'PREDICATE': [0],  # intersects
                'DISCARD_NONMATCHING': True,
                'PREFIX': '',
                'NON_MATCHING': 'memory:',
                'OUTPUT': 'memory:'
            })
            sb_in_pov  = pov_join['OUTPUT']
            sb_isolados = pov_join['NON_MATCHING']

            # Tag each group
            tagged_pov = processing.run('native:fieldcalculator', {
                'INPUT': sb_in_pov,
                'FIELD_NAME': 'POV_ISO', 'FIELD_TYPE': 2,
                'FIELD_LENGTH': 30, 'FORMULA': "'povoamento'",
                'OUTPUT': 'memory:'
            })['OUTPUT']

            tagged_iso = processing.run('native:fieldcalculator', {
                'INPUT': sb_isolados,
                'FIELD_NAME': 'POV_ISO', 'FIELD_TYPE': 2,
                'FIELD_LENGTH': 30, 'FORMULA': "'isolados'",
                'OUTPUT': 'memory:'
            })['OUTPUT']

            # Merge both tagged layers
            merged = processing.run('native:mergevectorlayers', {
                'LAYERS': [tagged_pov, tagged_iso],
                'CRS': source_layer.crs().authid(),
                'OUTPUT': 'memory:'
            })['OUTPUT']

            # Find trees directly overlapping infrastructure
            affected = processing.run('native:joinattributesbylocation', {
                'INPUT': merged,
                'JOIN': infra_total,
                'JOIN_FIELDS': [],
                'METHOD': 0,
                'PREDICATE': [0],  # intersects
                'DISCARD_NONMATCHING': True,
                'PREFIX': '',
                'OUTPUT': 'memory:'
            })
            if affected['OUTPUT'].featureCount() > 0:
                sb_az_afectados = affected['OUTPUT']
                sb_az_afectados.setName('SB_AZ_AFECTADOS')
                QgsProject.instance().addMapLayer(sb_az_afectados)
            else:
                self.log('Nenhuma árvore directamente afectada pelas infraestruturas')

        return areas_afectadas, sb_az_afectados
