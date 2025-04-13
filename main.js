const { app, BrowserWindow } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let mainWindow
let serverProcess

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  })

  mainWindow.loadFile('index.html')

  mainWindow.on('closed', function () {
    if (serverProcess) serverProcess.kill()
    mainWindow = null
  })
}

app.whenReady().then(() => {
  serverProcess = spawn('uvicorn', ['main:app', '--port', '8000'])
  createWindow()
})
