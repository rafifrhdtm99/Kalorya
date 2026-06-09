// app.js
document.addEventListener('DOMContentLoaded', () => {
    // Add subtle animation to the progress ring
    setTimeout(() => {
        const ring = document.querySelector('.ring-progress');
        // Example: animate to a specific percentage (1250 / 1800 is ~69%)
        ring.style.strokeDashoffset = '135';
    }, 500);

    // Camera Button Click interaction
    const snapBtn = document.getElementById('snapBtn');
    snapBtn.addEventListener('click', () => {
        // In MVP, just show an alert
        alert("Buka Kamera 📸\n\nNantinya AI akan mengenali foto makananmu otomatis di sini!");
    });
});
