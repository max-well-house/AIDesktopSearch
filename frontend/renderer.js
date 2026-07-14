const statusEl = document.getElementById('status')

async function loadHello() {
  const result = await window.api.getHello()

  if (result.ok) {
    statusEl.className = 'ok'
    statusEl.textContent =
      `OK from ${result.url}\n\n` + JSON.stringify(result.data, null, 2)
    return
  }

  statusEl.className = 'err'
  statusEl.textContent =
    `Connection error talking to ${result.url}\n\n` +
    `${result.error}\n\n` +
    'Is the backend running?\n' +
    'cd backend\n' +
    'uvicorn main:app --reload'
}

loadHello()
