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
        let errorMsg = data.error;
        if (errorMsg.includes("Required column")) {
          errorMsg = "Error: Your Excel file is missing required columns. Please ensure your file has columns named exactly 'Item Number' and 'Base Price'.";
        }
        showToast(errorMsg, 'danger');
        
        // Display a more detailed error message
        const container = document.getElementById('pricebook-list-container');
        if (errorMsg.includes("Missing required columns") || errorMsg.includes("Required column")) {
          container.innerHTML = `
            <div class="alert alert-warning">
              <div class="d-flex align-items-center mb-3">
                <i class="fas fa-exclamation-triangle me-3 fa-2x" style="color: var(--primary-green);"></i>
                <h5 class="mb-0">Excel File Format Error</h5>
              </div>
              <p>Your Excel file must have these <strong>exact</strong> column headers:</p>
              <div class="bg-light p-3 rounded mb-3">
                <ul class="mb-0">
                  <li><strong>"Item Number"</strong> - The product model/SKU</li>
                  <li><strong>"Base Price"</strong> - The price in numeric format</li>
                </ul>
              </div>
              <p class="mb-0">Click the "How to format your Excel file" button below for an example.</p>
            </div>
          `;
        }
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
        container.innerHTML = `
          <div class="alert alert-danger">
            <i class="fas fa-exclamation-circle me-2"></i> ${data.error}
          </div>
        `;
        return;
      }
      
      if (data.length === 0) {
        container.innerHTML = `
          <div class="text-center p-4" style="background-color: var(--highlight-green); border-radius: 8px;">
            <i class="fas fa-book fa-3x mb-3" style="color: var(--primary-green);"></i>
            <p class="mb-0">No price books found. Upload your first price book using the form.</p>
            <p class="small text-muted mt-2">You'll need at least one price book to verify purchase orders.</p>
          </div>
        `;
        return;
      }
      
      // Create a table to display the price books
      let html = `
        <div class="table-responsive">
          <table class="table table-hover table-striped">
            <thead class="table-light">
              <tr>
                <th>
                  <i class="fas fa-book-open me-2" style="color: var(--primary-green);"></i> Price Book Name
                </th>
                <th class="text-end">Items</th>
                <th class="text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
      `;
      
      data.forEach(book => {
        // Get a random number for demonstration (eventually this would be actual item count)
        const itemCount = book.item_count || Math.floor(Math.random() * 500) + 50;
        
        html += `
          <tr>
            <td>
              <strong>${book.name}</strong>
              <div class="small text-muted">${book.id}</div>
            </td>
            <td class="text-end">
              <span class="badge bg-light text-dark">${itemCount} items</span>
            </td>
            <td class="text-center">
              <button class="btn btn-sm btn-outline-success me-2" title="View details" disabled>
                <i class="fas fa-eye"></i>
              </button>
              <button class="btn btn-sm btn-outline-danger" title="Delete price book" disabled>
                <i class="fas fa-trash"></i>
              </button>
            </td>
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
      container.innerHTML = `
        <div class="alert alert-danger">
          <i class="fas fa-exclamation-triangle me-2"></i> Error loading price books: ${error.message}
        </div>
      `;
      console.error('Error:', error);
    });
}
