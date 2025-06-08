// Initialize tooltips
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
});

// Initialize popovers
var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl);
});

// Auto-dismiss alerts after 5 seconds
setTimeout(function() {
    var alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        var bsAlert = new bootstrap.Alert(alert);
        setTimeout(function() {
            bsAlert.close();
        }, 5000);
    });
}, 1000);

// File input preview for audio upload
function updateFileInfo(input) {
    const fileInfo = document.getElementById('fileInfo');
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const fileSize = (file.size / (1024 * 1024)).toFixed(2); // Convert to MB
        
        fileInfo.innerHTML = `
            <div class="alert alert-info alert-dismissible fade show mt-2">
                <i class="fas fa-file-audio me-2"></i>
                <strong>${file.name}</strong> (${fileSize} MB)
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        // Auto-dismiss the file info after 10 seconds
        setTimeout(() => {
            const alert = fileInfo.querySelector('.alert');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 10000);
    }
}

// Handle form submissions with loading state
document.addEventListener('submit', function(e) {
    const form = e.target;
    const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
    
    if (submitButton && !form.classList.contains('no-loading')) {
        const originalText = submitButton.innerHTML;
        const spinner = document.createElement('span');
        spinner.className = 'spinner-border spinner-border-sm me-2';
        spinner.setAttribute('role', 'status');
        spinner.setAttribute('aria-hidden', 'true');
        
        submitButton.disabled = true;
        submitButton.innerHTML = '';
        submitButton.appendChild(spinner);
        submitButton.appendChild(document.createTextNode(' Processing...'));
        
        // Revert the button if the form submission fails
        setTimeout(function() {
            if (submitButton.disabled) {
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        }, 10000);
    }
});

// Toggle password visibility
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const icon = document.querySelector(`[onclick="togglePasswordVisibility('${inputId}')"] i`);
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// Handle file upload progress
function handleFileUploadProgress(event) {
    if (event.lengthComputable) {
        const percentComplete = (event.loaded / event.total) * 100;
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = percentComplete + '%';
            progressBar.setAttribute('aria-valuenow', percentComplete);
            progressBar.textContent = Math.round(percentComplete) + '%';
        }
    }
}

// Initialize audio player for preview
function initAudioPlayer(audioElementId, playButtonId, progressBarId, timeDisplayId) {
    const audio = document.getElementById(audioElementId);
    const playButton = document.getElementById(playButtonId);
    const progressBar = document.getElementById(progressBarId);
    const timeDisplay = document.getElementById(timeDisplayId);
    
    if (!audio || !playButton) return;
    
    // Toggle play/pause
    playButton.addEventListener('click', function() {
        if (audio.paused) {
            audio.play();
            this.innerHTML = '<i class="fas fa-pause"></i>';
        } else {
            audio.pause();
            this.innerHTML = '<i class="fas fa-play"></i>';
        }
    });
    
    // Update progress bar
    audio.addEventListener('timeupdate', function() {
        if (progressBar) {
            const progress = (audio.currentTime / audio.duration) * 100;
            progressBar.style.width = progress + '%';
        }
        
        if (timeDisplay) {
            const minutes = Math.floor(audio.currentTime / 60);
            const seconds = Math.floor(audio.currentTime % 60);
            timeDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
    });
    
    // Handle audio end
    audio.addEventListener('ended', function() {
        playButton.innerHTML = '<i class="fas fa-play"></i>';
        if (progressBar) {
            progressBar.style.width = '0%';
        }
        if (timeDisplay) {
            timeDisplay.textContent = '0:00';
        }
    });
}

// Initialize audio players on page load
document.addEventListener('DOMContentLoaded', function() {
    // Find all audio players on the page and initialize them
    const audioPlayers = document.querySelectorAll('[data-audio-player]');
    audioPlayers.forEach((player, index) => {
        const audioId = player.getAttribute('data-audio-player');
        const playButtonId = `playButton${index}`;
        const progressBarId = `progressBar${index}`;
        const timeDisplayId = `timeDisplay${index}`;
        
        initAudioPlayer(audioId, playButtonId, progressBarId, timeDisplayId);
    });
    
    // Handle tab switching
    const tabLinks = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabLinks.forEach(link => {
        link.addEventListener('shown.bs.tab', function (e) {
            window.dispatchEvent(new Event('resize'));
        });
    });
});

// Copy to clipboard functionality
function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(function() {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        button.classList.add('btn-success');
        
        setTimeout(function() {
            button.innerHTML = originalText;
            button.classList.remove('btn-success');
        }, 2000);
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
    });
}

// Handle dark mode toggle
function toggleDarkMode() {
    const html = document.documentElement;
    const isDark = html.getAttribute('data-bs-theme') === 'dark';
    
    if (isDark) {
        html.removeAttribute('data-bs-theme');
        localStorage.setItem('theme', 'light');
    } else {
        html.setAttribute('data-bs-theme', 'dark');
        localStorage.setItem('theme', 'dark');
    }
    
    // Update the icon
    const icon = document.querySelector('.dark-mode-toggle i');
    if (icon) {
        icon.className = isDark ? 'fas fa-moon' : 'fas fa-sun';
    }
}

// Check for saved theme preference
function checkThemePreference() {
    const theme = localStorage.getItem('theme') || 'light';
    const html = document.documentElement;
    
    if (theme === 'dark') {
        html.setAttribute('data-bs-theme', 'dark');
    } else {
        html.removeAttribute('data-bs-theme');
    }
    
    // Update the icon
    const icon = document.querySelector('.dark-mode-toggle i');
    if (icon) {
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', checkThemePreference);

// Handle form validation
function validateForm(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('[required]');
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// Add event listeners for form validation
const forms = document.querySelectorAll('form[novalidate]');
forms.forEach(form => {
    form.addEventListener('submit', function(e) {
        if (!validateForm(this)) {
            e.preventDefault();
            e.stopPropagation();
        }
    });
    
    // Clear validation on input
    const inputs = form.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.addEventListener('input', function() {
            if (this.value.trim()) {
                this.classList.remove('is-invalid');
            }
        });
    });
});
