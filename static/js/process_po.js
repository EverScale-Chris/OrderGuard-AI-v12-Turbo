document.addEventListener('DOMContentLoaded', function() {
  // Load price books for the dropdown
  loadPriceBooksDropdown();
  
  // Set up form submission handler
  const form = document.getElementById('process-po-form');
  form.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const priceBookSelect = document.getElementById('pricebook-select');
    const fileInput = document.getElementById('po-file');
    
    // Validate inputs
    if (priceBookSelect.value === '') {
      showToast('Please select a price book', 'warning');
      return;
    }
    
    if (!fileInput.files || fileInput.files.length === 0) {
      showToast('Please select a PDF file', 'warning');
      return;
    }
    
    // Create FormData object
    const formData = new FormData();
    formData.append('pricebook_id', priceBookSelect.value);
    formData.append('file', fileInput.files[0]);
    
    // Show spinner and disable button
    const button = document.getElementById('process-btn');
    const spinner = document.getElementById('process-spinner');
    button.disabled = true;
    spinner.classList.remove('d-none');
    
    // Clear previous results
    document.getElementById('results-container').innerHTML = `
      <div class="d-flex justify-content-center align-items-center" style="min-height: 300px;">
        <div class="text-center">
          <div class="spinner-border text-primary mb-3" role="status">
            <span class="visually-hidden">Processing...</span>
          </div>
          <p>Processing Purchase Order...<br>This may take a minute.</p>
        </div>
      </div>
    `;
    
    // Submit the form
    fetch('/api/process-po', {
      method: 'POST',
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        showToast(data.error, 'danger');
        document.getElementById('results-container').innerHTML = `
          <div class="alert alert-danger">
            <h5>Error Processing Purchase Order</h5>
            <p>${data.error}</p>
          </div>
        `;
      } else {
        showToast('Purchase Order processed successfully', 'success');
        displayResults(data);
      }
    })
    .catch(error => {
      showToast('An error occurred: ' + error.message, 'danger');
      console.error('Error:', error);
      document.getElementById('results-container').innerHTML = `
        <div class="alert alert-danger">
          <h5>Error Processing Purchase Order</h5>
          <p>An unexpected error occurred: ${error.message}</p>
        </div>
      `;
    })
    .finally(() => {
      // Hide spinner and enable button
      button.disabled = false;
      spinner.classList.add('d-none');
    });
  });
  
  // Set up copy to clipboard button
  const copyBtn = document.getElementById('copy-btn');
  copyBtn.addEventListener('click', function() {
    const textarea = document.getElementById('email-report');
    if (textarea) {
      textarea.select();
      document.execCommand('copy');
      showToast('Email report copied to clipboard', 'success');
    }
  });
});

/**
 * Loads the list of price books into the dropdown
 */
function loadPriceBooksDropdown() {
  const select = document.getElementById('pricebook-select');
  
  fetch('/api/pricebooks')
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        select.innerHTML = `<option value="" disabled selected>Error loading price books</option>`;
        return;
      }
      
      if (data.length === 0) {
        select.innerHTML = `<option value="" disabled selected>No price books available</option>`;
        return;
      }
      
      select.innerHTML = `<option value="" disabled selected>Select a price book</option>`;
      
      data.forEach(book => {
        const option = document.createElement('option');
        option.value = book.id;
        option.textContent = book.name;
        select.appendChild(option);
      });
    })
    .catch(error => {
      select.innerHTML = `<option value="" disabled selected>Error loading price books</option>`;
      console.error('Error:', error);
    });
}

/**
 * Displays the results of processing a Purchase Order
 * @param {Object} data - The response data from the server
 */
function displayResults(data) {
  const container = document.getElementById('results-container');
  const copyBtn = document.getElementById('copy-btn');
  
  // Create the results display
  let html = `
    <div class="mb-3">
      <label for="email-report" class="form-label">Email Report</label>
      <textarea class="form-control font-monospace" id="email-report" rows="12" readonly>${data.email_report}</textarea>
    </div>
  `;
  
  // Create a summary table of the results
  html += `
    <h5>Summary of Line Items</h5>
    <div class="table-responsive">
      <table class="table table-sm">
        <thead>
          <tr>
            <th>Model Number</th>
            <th>Notes</th>
            <th>PO Price</th>
            <th>Book Price</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
  `;
  
  data.comparison_results.forEach(item => {
    let statusClass = '';
    switch (item.status) {
      case 'Match':
        statusClass = 'text-success';
        break;
      case 'Mismatch':
        statusClass = 'text-danger';
        break;
      case 'Model Not Found':
        statusClass = 'text-warning';
        break;
      case 'Price Format Error':
        statusClass = 'text-danger';
        break;
      default:
        statusClass = 'text-muted';
    }
    
    // We'll keep the description column focused on showing just the model number
    // that was found in the description (if any)
    const descOutput = item.status === 'Model Not Found' && item.description 
      ? 'No match found in description' 
      : '';
    
    html += `
      <tr>
        <td>${item.model}</td>
        <td>${descOutput}</td>
        <td>$${item.po_price}</td>
        <td>${item.book_price ? '$' + item.book_price : '-'}</td>
        <td class="${statusClass}">${item.status}</td>
      </tr>
    `;
  });
  
  html += `
        </tbody>
      </table>
    </div>
  `;
  
  container.innerHTML = html;
  copyBtn.disabled = false;
}
