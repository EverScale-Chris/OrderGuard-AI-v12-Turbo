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
  
  // Create a summary table of the results - now first
  let html = `
    <div class="card mb-4">
      <div class="card-header">
        <h5 class="mb-0"><i class="fas fa-table"></i> Summary of Line Items</h5>
      </div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-striped table-hover mb-0">
            <thead class="table-light">
              <tr>
                <th>Model Number</th>
                <th>Notes</th>
                <th>PO Price</th>
                <th>Book Price</th>
                <th>Difference</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
  `;
  
  data.comparison_results.forEach(item => {
    let statusClass = '';
    let priceCompareClass = '';
    let priceDifference = '';
    
    switch (item.status) {
      case 'Match':
        statusClass = 'text-success';
        break;
      case 'Mismatch':
        statusClass = 'text-danger';
        
        // Calculate and format the price difference with color coding
        if (item.book_price && item.po_price) {
          const diff = parseFloat(item.book_price) - parseFloat(item.po_price);
          if (diff > 0) {
            // PO price is lower than book price (PO is cheaper)
            priceCompareClass = 'text-price-higher';
            priceDifference = `+$${Math.abs(diff).toFixed(2)}`;
          } else if (diff < 0) {
            // PO price is higher than book price (PO is more expensive)
            priceCompareClass = 'text-price-lower';
            priceDifference = `-$${Math.abs(diff).toFixed(2)}`;
          }
        }
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
        <td><strong>${item.model}</strong></td>
        <td>${descOutput}</td>
        <td>$${parseFloat(item.po_price).toFixed(2)}</td>
        <td>${item.book_price ? '$' + parseFloat(item.book_price).toFixed(2) : '-'}</td>
        <td class="${priceCompareClass}"><strong>${priceDifference}</strong></td>
        <td class="${statusClass}"><strong>${item.status}</strong></td>
      </tr>
    `;
  });
  
  html += `
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    
    <!-- Email report section (now below the summary) -->
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0"><i class="fas fa-envelope"></i> Email Report</h5>
        <button class="btn btn-sm btn-outline-success" id="copy-btn">
          <i class="fas fa-copy"></i> Copy to Clipboard
        </button>
      </div>
      <div class="card-body">
        <textarea class="form-control font-monospace" id="email-report" rows="12" readonly>${data.email_report}</textarea>
        <div class="form-text text-muted mt-2">
          <i class="fas fa-info-circle"></i> Copy this report to send to your team or customer service.
        </div>
      </div>
    </div>
  `;
  
  // Add the HTML to the container
  container.innerHTML = html;
  
  // Re-initialize the copy button event listener (since we recreated the DOM element)
  const copyButton = document.getElementById('copy-btn');
  if (copyButton) {
    copyButton.addEventListener('click', function() {
      const textarea = document.getElementById('email-report');
      if (textarea) {
        textarea.select();
        document.execCommand('copy');
        showToast('Email report copied to clipboard', 'success');
      }
    });
  }
}
