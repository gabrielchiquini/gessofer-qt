import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Backend

Rectangle {
    id: productList
    color: Constants.contentBg
    Layout.fillWidth: true
    Layout.fillHeight: true

    ColumnLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.margins: 10
        spacing: 5

        // ── Filter Form Section ─────────────────────────────
        RowLayout {
            Layout.fillWidth: true

            Label {
                text: "Fornecedor"
            }
            TextField {
                id: filterSupplier
                Layout.fillWidth: true
            }

            Label {
                text: "Produto"
            }
            TextField {
                id: filterProduct
                Layout.fillWidth: true
            }

            Label {
                text: "Mês"
            }
            TextField {
                id: filterMonth
                Layout.preferredWidth: 100
                inputMask: "99/9999"
            }

            Button {
                text: "Consultar"
                onClicked: productList.onSearch()
            }

            Button {
                text: "Limpar"
                onClicked: productList.onClear()
            }
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true

            TableView {
                id: tableView
                anchors.fill: parent
                clip: true

                model: ProductListModel {}

                delegate: Rectangle {
                    implicitWidth: 100
                    implicitHeight: 20
                    border.width: 1

                    Text {
                        text: "display"
                        font.pixelSize: 14
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Button {
                text: "←"
                enabled: tableView.model.currentPage > 1
                onClicked: tableView.model.refresh(tableView.model.currentPage - 1, filterSupplier.text, filterProduct.text, filterMonth.text)
            }

            Label {
                text: "Página " + tableView.model.currentPage + " de " + tableView.model.pageCount
            }

            Button {
                text: "→"
                enabled: tableView.model.currentPage < tableView.model.pageCount
                onClicked: tableView.model.refresh(tableView.model.currentPage + 1, filterSupplier.text, filterProduct.text, filterMonth.text)
            }
        }
    }

    // ── Logic ─────────────────────────────────────────────
    function onSearch() {
        var supplier = filterSupplier.text;
        var product = filterProduct.text;
        var month = filterMonth.text;
        tableView.model.refresh(1, supplier, product, month);
        tableView.forceLayout();
    }

    function onClear() {
        filterSupplier.text = "";
        filterProduct.text = "";
        filterMonth.text = "";
        tableView.model.refresh(1, "", "", "");
        tableView.forceLayout();
    }

    Component.onCompleted: {
        onClear();
    }
}
