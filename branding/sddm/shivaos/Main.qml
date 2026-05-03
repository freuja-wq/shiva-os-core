import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SddmComponents 2.0

Rectangle {
    id: root
    width: 1920; height: 1080
    color: "#0a0a0a"

    // Fond wallpaper
    Image {
        anchors.fill: parent
        source: "background.png"
        fillMode: Image.PreserveAspectCrop
    }

    // Overlay glass
    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.45
    }

    // Logo + titre centré en haut
    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 80
        spacing: 12

        Image {
            source: "shivaos-logo-128.png"
            width: 128; height: 128
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Text {
            text: "SHIVA OS"
            color: "#FF8C00"
            font.family: "Arial Black"
            font.pixelSize: 42
            font.bold: true
            font.letterSpacing: 8
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Text {
            text: "Pure Gaming Ecosystem"
            color: "#FF8C00"
            opacity: 0.5
            font.pixelSize: 16
            font.letterSpacing: 4
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }

    // Carte de login centrée
    Rectangle {
        id: loginCard
        width: 380; height: 300
        anchors.centerIn: parent
        anchors.verticalCenterOffset: 40
        color: Qt.rgba(1, 1, 1, 0.04)
        border.color: Qt.rgba(1, 1, 1, 0.1)
        border.width: 1
        radius: 24

        Column {
            anchors.centerIn: parent
            spacing: 18
            width: 300

            // Champ mot de passe
            TextField {
                id: pwField
                width: parent.width
                height: 50
                echoMode: TextInput.Password
                placeholderText: "Mot de passe"
                color: "white"
                font.pixelSize: 16
                background: Rectangle {
                    color: Qt.rgba(1,1,1,0.06)
                    border.color: pwField.activeFocus ? "#FF8C00" : Qt.rgba(1,1,1,0.15)
                    border.width: 1
                    radius: 12
                }
                leftPadding: 16
                Keys.onReturnPressed: loginBtn.clicked()
            }

            // Bouton login
            Rectangle {
                id: loginBtn
                width: parent.width; height: 50
                color: loginMouse.containsMouse ? "#e67e00" : "#FF8C00"
                radius: 12
                property bool clicked: false

                Text {
                    text: "ENTRER DANS LA FORGE"
                    anchors.centerIn: parent
                    color: "black"
                    font.pixelSize: 13
                    font.bold: true
                    font.letterSpacing: 2
                }
                MouseArea {
                    id: loginMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        sddm.login(userModel.data(userModel.index(0,0), 257), pwField.text, sessionIndex)
                    }
                }
                Behavior on color { ColorAnimation { duration: 150 } }
            }
        }
    }

    // Heure en bas à droite
    Text {
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.margins: 30
        text: Qt.formatTime(new Date(), "hh:mm")
        color: "#FF8C00"
        opacity: 0.5
        font.pixelSize: 22
        font.bold: true
    }

    // Version en bas à gauche
    Text {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 30
        text: "Shiva OS 2.0 — shivaos.com"
        color: "#FF8C00"
        opacity: 0.3
        font.pixelSize: 13
        font.letterSpacing: 2
    }

    property int sessionIndex: sessionModel.lastIndex

    Component.onCompleted: {
        if (userModel.count > 0) pwField.forceActiveFocus()
    }
}
