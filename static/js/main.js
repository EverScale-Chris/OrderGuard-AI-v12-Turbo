/**
 * Shows a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, danger, warning, info)
 */
function showToast(message, type = 'info') {
  const toastContainer = document.getElementById('toast-container');
  
  const toastId = 'toast-' + Date.now();
  
  // Custom styling based on message type
  let bgColor, icon, textColor;
  switch(type) {
    case 'success':
      bgColor = '#d1e7dd';
      textColor = '#0f5132';
      icon = '<i class="fas fa-check-circle me-2"></i>';
      break;
    case 'danger':
      bgColor = '#f8d7da';
      textColor = '#842029';
      icon = '<i class="fas fa-exclamation-circle me-2"></i>';
      break;
    case 'warning':
      bgColor = '#fff3cd';
      textColor = '#664d03';
      icon = '<i class="fas fa-exclamation-triangle me-2"></i>';
      break;
    default: // info
      bgColor = '#e5f5ea';
      textColor = '#1a5336';
      icon = '<i class="fas fa-info-circle me-2"></i>';
  }
  
  const toastHTML = `
    <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" 
         style="background-color: ${bgColor}; color: ${textColor}; border-left: 4px solid var(--primary-green);">
      <div class="d-flex">
        <div class="toast-body">
          ${icon} ${message}
        </div>
        <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;
  
  toastContainer.insertAdjacentHTML('beforeend', toastHTML);
  
  const toastElement = document.getElementById(toastId);
  const toast = new bootstrap.Toast(toastElement, { 
    animation: true,
    autohide: true,
    delay: 5000
  });
  toast.show();
  
  // Remove the toast from the DOM after it's hidden
  toastElement.addEventListener('hidden.bs.toast', () => {
    toastElement.remove();
  });
}

/**
 * Generic form submission handler for file uploads with progress indication
 * @param {HTMLFormElement} form - The form element
 * @param {string} url - The URL to submit the form to
 * @param {function} onSuccess - Callback for successful submission
 * @param {string} buttonId - ID of the submit button
 * @param {string} spinnerId - ID of the spinner element
 */
function handleFormSubmit(form, url, onSuccess, buttonId, spinnerId) {
  const formData = new FormData(form);
  const button = document.getElementById(buttonId);
  const spinner = document.getElementById(spinnerId);
  
  // Show spinner
  button.disabled = true;
  spinner.classList.remove('d-none');
  
  fetch(url, {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      showToast(data.error, 'danger');
    } else {
      onSuccess(data);
    }
  })
  .catch(error => {
    showToast('An error occurred: ' + error.message, 'danger');
    console.error('Error:', error);
  })
  .finally(() => {
    // Hide spinner
    button.disabled = false;
    spinner.classList.add('d-none');
  });
}
