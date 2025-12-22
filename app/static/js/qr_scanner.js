const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const statusDiv = document.getElementById('status');
const resultArea = document.getElementById('result-area');

let scanning = false;
let stream = null;

function updateStatus(type, text) {
    statusDiv.className = 'status-indicator status-' + type;
    statusDiv.innerHTML = `<i class="bi bi-${getIcon(type)}"></i> ${text}`;
}

function getIcon(type) {
    const icons = {
        ready: 'camera-video',
        scanning: 'search',
        error: 'exclamation-triangle',
    };
    return icons[type] || 'camera-video';
}

function showError(message) {
    scanning = false;
    stopBtn.style.display = 'none';
    startBtn.style.display = 'inline-block';
    updateStatus('error', 'Error');

    resultArea.innerHTML = `
        <div class="alert alert-danger">
            <h6><i class="bi bi-x-circle"></i> Error</h6>
            <p>${message}</p>
            <button class="btn btn-primary btn-sm w-100 mt-2" onclick="location.reload()">
                <i class="bi bi-arrow-clockwise"></i> Scan Ulang
            </button>
        </div>
    `;
}

async function initCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        updateStatus('error', 'Browser tidak support');
        resultArea.innerHTML = `
            <div class="alert alert-danger">
                <strong>Browser Tidak Didukung</strong>
                <p>Browser ini tidak mendukung akses kamera.</p>
                <ul class="small">
                    <li>Gunakan Chrome, Edge, atau Firefox versi terbaru</li>
                    <li>Pastikan browser diperbarui</li>
                </ul>
            </div>
        `;
        return;
    }

    try {
        const constraints = {
            video: {
                facingMode: 'environment',
            },
        };
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = stream;

        video.addEventListener('loadedmetadata', function () {
            startBtn.disabled = false;
            updateStatus('ready', 'Ready');
        });
    } catch (err) {
        let errorMessage = 'Gagal Mengakses Kamera';
        let errorDetail = err.message || '';
        let suggestions = '';

        if (err.name === 'NotAllowedError' || err.name === 'SecurityError') {
            errorMessage = 'Izin Kamera Ditolak';
            errorDetail = 'Aplikasi tidak mendapat izin untuk menggunakan kamera';
            suggestions = `
                <strong>Solusi:</strong>
                <ol class="small">
                    <li>Cek icon kamera di address bar</li>
                    <li>Ubah izin Camera menjadi "Allow"</li>
                    <li>Reload halaman ini</li>
                </ol>
            `;
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
            errorMessage = 'Kamera Tidak Ditemukan';
            errorDetail = 'Tidak ada kamera yang tersedia';
            suggestions = `
                <strong>Solusi:</strong>
                <ul class="small">
                    <li>Pastikan webcam terpasang</li>
                    <li>Cek driver kamera</li>
                </ul>
            `;
        } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
            errorMessage = 'Kamera Sedang Digunakan';
            errorDetail = 'Kamera sedang digunakan aplikasi lain';
            suggestions = `
                <strong>Solusi:</strong>
                <ul class="small">
                    <li>Tutup aplikasi lain yang menggunakan kamera</li>
                    <li>Reload halaman ini</li>
                </ul>
            `;
        } else if (err.name === 'NotSupportedError') {
            errorMessage = 'HTTPS Diperlukan';
            errorDetail = 'Akses kamera memerlukan koneksi aman';
            suggestions = `
                <strong>Solusi:</strong>
                <ul class="small">
                    <li>Akses via: <code>http://localhost:5000/scan</code></li>
                    <li>JANGAN gunakan IP address (127.0.0.1 atau 192.168.x.x)</li>
                    <li>Atau gunakan HTTPS di production</li>
                </ul>
            `;
        }

        updateStatus('error', 'Error');
        resultArea.innerHTML = `
            <div class="alert alert-danger">
                <h6><i class="bi bi-exclamation-triangle"></i> ${errorMessage}</h6>
                <small class="text-muted">${errorDetail}</small>
                <hr>
                ${suggestions}
                <button class="btn btn-primary btn-sm mt-2 w-100" onclick="location.reload()">
                    <i class="bi bi-arrow-clockwise"></i> Muat Ulang
                </button>
            </div>
        `;
    }
}

function tick() {
    if (!scanning) return;

    if (video.readyState === video.HAVE_ENOUGH_DATA) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'dontInvert',
        });

        if (code) {
            console.log('QR Code detected:', code.data);
            handleQRCode(code.data);
        }
    }

    requestAnimationFrame(tick);
}

function handleQRCode(data) {
    scanning = false;
    stopBtn.style.display = 'none';
    startBtn.style.display = 'inline-block';
    updateStatus('ready', 'QR Terdeteksi!');

    resultArea.innerHTML = `
        <div class="alert alert-success">
            <h6><i class="bi bi-check-circle"></i> QR Code Terdeteksi!</h6>
            <small class="text-break">${data}</small>
        </div>
        <div class="text-center mt-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2"><strong>Redirect...</strong></p>
        </div>
    `;

    if (data.includes('/public/aset/') || data.includes('/aset/detail/')) {
        const match = data.match(/\/(?:public\/)?aset\/(?:detail\/)?(\d+)/);
        if (match) {
            const assetId = match[1];
            setTimeout(() => {
                window.location.href = `/public/aset/${assetId}`;
            }, 1000);
        } else {
            showError('URL tidak valid');
        }
    } else {
        showError('QR Code bukan dari sistem ini');
    }
}

startBtn.addEventListener('click', function () {
    scanning = true;
    startBtn.style.display = 'none';
    stopBtn.style.display = 'inline-block';
    updateStatus('scanning', 'Scanning...');

    resultArea.innerHTML = `
        <div class="alert alert-info">
            <i class="bi bi-search"></i>
            <strong>Sedang Scan...</strong><br>
            <small>Arahkan QR Code ke kamera</small>
        </div>
    `;

    tick();
});

stopBtn.addEventListener('click', function () {
    scanning = false;
    stopBtn.style.display = 'none';
    startBtn.style.display = 'inline-block';
    updateStatus('ready', 'Ready');

    resultArea.innerHTML = `
        <p class="text-muted text-center">
            <i class="bi bi-qr-code" style="font-size: 3rem;"></i><br>
            Scan dihentikan
        </p>
    `;
});

window.addEventListener('beforeunload', function () {
    if (stream) {
        stream.getTracks().forEach((track) => track.stop());
    }
});

initCamera();
