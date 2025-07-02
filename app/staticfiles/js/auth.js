document.addEventListener('DOMContentLoaded', function() {
    // Toggle password visibility
    const togglePasswordButtons = document.querySelectorAll('.toggle-password');
    
    togglePasswordButtons.forEach(button => {
        button.addEventListener('click', function() {
            const input = this.previousElementSibling;
            const icon = this.querySelector('i');
            
            // Toggle the input type
            const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
            input.setAttribute('type', type);
            
            // Toggle the eye icon
            icon.classList.toggle('bi-eye');
            icon.classList.toggle('bi-eye-slash');
            
            // Update the tooltip title
            const title = type === 'password' ? 'Show password' : 'Hide password';
            this.setAttribute('title', title);
            
            // Update the tooltip if it's already shown
            const tooltip = bootstrap.Tooltip.getInstance(this);
            if (tooltip) {
                tooltip.setContent({ '.tooltip-inner': title });
            }
        });
    });
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Add validation classes on form submission
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});
