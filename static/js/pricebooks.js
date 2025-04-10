document.addEventListener('DOMContentLoaded', function() {
  // Load price books on page load
  loadPriceBooks();
  
  // Set up form submission handler
  const form = document.getElementById('upload-pricebook-form');
  form.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const nameInput = document.getElementById('pricebook-name');
    const fileInput = document.getElementById('pricebook-file');
    
    // Validate inputs
    if (!nameInput.value.trim()) {
      showToast('Please enter a price book name', 'warning');
      return;
    }
    
    if (!fileInput.files || fileInput.files.length === 0) {
      showToast('Please select an Excel file', 'warning');
      return;
    }
    
    // Create FormData object
    const formData = new FormData();
    formData.append('pricebook_name', nameInput.value.trim());
    formData.append('file', fileInput.files[0]);
    
    // Show spinner
    const button = document.getElementById('upload-btn');
    const spinner = document.getElementById('upload-spinner');
    button.disabled = true;
    spinner.classList.remove('d-none');
    
    // Submit the form
    fetch('/api/pricebooks', {
      method: 'POST',
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        showToast(data.error, 'danger');
      } else {
        showToast(data.message, 'success');
        form.reset();
        loadPriceBooks(); // Reload the price book list
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
  });
});

/**
 * Loads the list of price books from the server
 */
function loadPriceBooks() {
  const container = document.getElementById('pricebook-list-container');
  
  fetch('/api/pricebooks')
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        container.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        return;
      }
      
      if (data.length === 0) {
        container.innerHTML = `
          <div class="text-center text-muted py-4">
            <i class="fas fa-book fa-3x mb-3"></i>
            <p>No price books found. Upload your first price book using the form.</p>
          </div>
        `;
        return;
      }
      
      // Create a table to display the price books
      let html = `
        <div class="table-responsive">
          <table class="table table-hover">
            <thead>
              <tr>
                <th>Price Book Name</th>
                <th>ID</th>
              </tr>
            </thead>
            <tbody>
      `;
      
      data.forEach(book => {
        html += `
          <tr>
            <td>${book.name}</td>
            <td><small class="text-muted">${book.id}</small></td>
          </tr>
        `;
      });
      
      html += `
            </tbody>
          </table>
        </div>
      `;
      
      container.innerHTML = html;
    })
    .catch(error => {
      container.innerHTML = `<div class="alert alert-danger">Error loading price books: ${error.message}</div>`;
      console.error('Error:', error);
    });
}
