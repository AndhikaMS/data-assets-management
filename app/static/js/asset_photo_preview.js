function setupPhotoPreview(inputId, previewContainerId, imageId) {
    const input = document.getElementById(inputId);
    const previewContainer = document.getElementById(previewContainerId);
    const image = document.getElementById(imageId);

    if (!input || !previewContainer || !image) {
        return;
    }

    input.addEventListener('change', function (e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function (event) {
                image.src = event.target.result;
                previewContainer.style.display = 'block';
            };
            reader.readAsDataURL(file);
        } else {
            previewContainer.style.display = 'none';
        }
    });
}

// Inisialisasi default untuk form dengan id standar
window.addEventListener('DOMContentLoaded', function () {
    setupPhotoPreview('photo', 'photoPreview', 'previewImage');
});
