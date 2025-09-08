from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from qtpy.QtWidgets import (
    QFileDialog,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    import napari
from napari.layers import Points


class ExampleQWidget(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer

        # Buttons
        self.annotation_button = QPushButton("Start Annotation")
        self.annotation_button.setCheckable(True)
        self.annotation_button.clicked.connect(self._toggle_annotation_mode)

        self.delete_button = QPushButton("Delete Selected Spot")
        self.delete_button.clicked.connect(self._delete_selected_spot)

        self.export_button = QPushButton("Export to CSV")
        self.export_button.clicked.connect(self._export_to_csv)

        # Spot list and text input
        self.spot_list_widget = QListWidget()
        self.spot_list_widget.itemClicked.connect(
            self._highlight_spot_in_viewer
        )

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter annotation text")
        self.text_input.returnPressed.connect(self._add_text_to_spot)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.annotation_button)
        layout.addWidget(self.spot_list_widget)
        layout.addWidget(self.text_input)
        layout.addWidget(self.delete_button)
        layout.addWidget(self.export_button)
        self.setLayout(layout)

        # Annotation layer
        self.annotation_layer: Points = None
        self.annotating = False
        self.annotations = []

        # Default colormap to avoid warnings
        self.color_dict = defaultdict(lambda: [1, 1, 1, 1])  # default white
        self.color_dict.update(
            {
                0: [1, 0, 0, 1],  # red
                1: [0, 0, 1, 1],  # blue
                None: [1, 1, 1, 1],  # default
            }
        )

    def _toggle_annotation_mode(self):
        self.annotating = not self.annotating
        if self.annotating:
            self.annotation_button.setText("Stop Annotation")
            self.viewer.mouse_drag_callbacks.append(self._add_annotation)
            self._setup_annotation_layer()
        else:
            self.annotation_button.setText("Start Annotation")
            self.viewer.mouse_drag_callbacks.remove(self._add_annotation)

    def _setup_annotation_layer(self):
        if self.annotation_layer is None:
            self.annotation_layer = self.viewer.add_points(
                np.empty((0, 2)),
                name="Annotations",
                size=8,
                face_color=[0, 0, 0, 0],  # transparent
                border_color=self.color_dict[None],  # default color
                symbol="o",
            )

    def _add_annotation(self, viewer, event):
        if not self.annotating:
            return
        coords = np.array(viewer.cursor.position)[2:]
        self.annotation_layer.data = np.vstack(
            [self.annotation_layer.data, coords]
        )
        self.annotations.append({"x": coords[0], "y": coords[1], "text": ""})
        self._update_spot_list()

    def _update_spot_list(self):
        self.spot_list_widget.clear()
        for i, annotation in enumerate(self.annotations, start=1):
            text = annotation["text"] if annotation["text"] else "No text"
            self.spot_list_widget.addItem(
                f"Spot {i}: (X={annotation['x']:.2f}, Y={annotation['y']:.2f}) - {text}"
            )

    def _highlight_spot_in_viewer(self, item):
        index = self.spot_list_widget.row(item)
        if index < 0 or index >= len(self.annotation_layer.data):
            return
        default_color = self.color_dict[None]
        self.annotation_layer.border_color = np.array(
            [default_color] * len(self.annotation_layer.data)
        )
        self.annotation_layer.border_color[index] = [
            1,
            0,
            0,
            1,
        ]  # highlight selected spot red
        self.annotation_layer.refresh()

    def _add_text_to_spot(self):
        selected_items = self.spot_list_widget.selectedItems()
        if not selected_items:
            return
        index = self.spot_list_widget.row(selected_items[0])
        text = self.text_input.text()
        if text:
            self.annotations[index]["text"] = text
            self._update_spot_list()
            self.text_input.clear()

    def _delete_selected_spot(self):
        selected_items = self.spot_list_widget.selectedItems()
        if not selected_items:
            return
        index = self.spot_list_widget.row(selected_items[0])
        self.annotation_layer.data = np.delete(
            self.annotation_layer.data, index, axis=0
        )
        del self.annotations[index]
        self._update_spot_list()

    def _export_to_csv(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Annotations", "", "CSV Files (*.csv)"
        )
        if filename:
            pd.DataFrame(self.annotations).to_csv(filename, index=False)
            print(f"Annotations exported to {filename}")
