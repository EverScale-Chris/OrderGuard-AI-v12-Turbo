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
  
  // First create a results overview card
  let matchCount = 0;
  let mismatchCount = 0;
  let notFoundCount = 0;
  
  // Count the statuses
  data.comparison_results.forEach(item => {
    if (item.status === 'Match') matchCount++;
    else if (item.status === 'Mismatch') mismatchCount++;
    else if (item.status === 'Model Not Found') notFoundCount++;
  });
  
  // Create HTML with status overview
  let html = `
    <div class="p-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h5 class="fw-semibold mb-0">Verification Complete</h5>
        <span class="badge bg-light text-dark px-3 py-2">
          ${data.comparison_results.length} items processed
        </span>
      </div>
      
      <div class="row g-3 mb-4">
        <div class="col-md-4">
          <div class="card border-0 bg-light rounded-4 h-100">
            <div class="card-body p-3 text-center">
              <div class="rounded-circle d-inline-flex align-items-center justify-content-center mb-3" 
                style="background-color: rgba(52, 199, 89, 0.1); width: 50px; height: 50px;">
                <i class="fas fa-check-circle fa-lg" style="color: var(--app-success);"></i>
              </div>
              <h3 class="fw-bold mb-0">${matchCount}</h3>
              <p class="small text-muted mb-0">Matching Prices</p>
            </div>
          </div>
        </div>
        
        <div class="col-md-4">
          <div class="card border-0 bg-light rounded-4 h-100">
            <div class="card-body p-3 text-center">
              <div class="rounded-circle d-inline-flex align-items-center justify-content-center mb-3" 
                style="background-color: rgba(255, 59, 48, 0.1); width: 50px; height: 50px;">
                <i class="fas fa-exclamation-circle fa-lg" style="color: var(--app-danger);"></i>
              </div>
              <h3 class="fw-bold mb-0">${mismatchCount}</h3>
              <p class="small text-muted mb-0">Price Discrepancies</p>
            </div>
          </div>
        </div>
        
        <div class="col-md-4">
          <div class="card border-0 bg-light rounded-4 h-100">
            <div class="card-body p-3 text-center">
              <div class="rounded-circle d-inline-flex align-items-center justify-content-center mb-3" 
                style="background-color: rgba(255, 149, 0, 0.1); width: 50px; height: 50px;">
                <i class="fas fa-question-circle fa-lg" style="color: var(--app-warning);"></i>
              </div>
              <h3 class="fw-bold mb-0">${notFoundCount}</h3>
              <p class="small text-muted mb-0">Not Found</p>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Summary table -->
    <div class="card mb-4 border-0 rounded-4 overflow-hidden">
      <div class="card-header bg-white py-3 px-4 border-0">
        <div class="d-flex align-items-center">
          <div class="rounded-circle d-flex align-items-center justify-content-center me-3" 
            style="background-color: var(--light-green); width: 32px; height: 32px;">
            <i class="fas fa-table" style="color: var(--primary-green);"></i>
          </div>
          <h6 class="fw-semibold mb-0">Line Item Details</h6>
        </div>
      </div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-hover mb-0">
            <thead style="background-color: var(--app-gray);">
              <tr>
                <th class="px-4 py-3 text-nowrap">Model Number</th>
                <th class="px-4 py-3">Notes</th>
                <th class="px-4 py-3 text-end">PO Price</th>
                <th class="px-4 py-3 text-end">Book Price</th>
                <th class="px-4 py-3 text-end">Difference</th>
                <th class="px-4 py-3 text-center">Status</th>
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
    
    // Create a badge for the status
    let statusBadge = '';
    switch (item.status) {
      case 'Match':
        statusBadge = `<span class="badge rounded-pill bg-success-subtle text-success px-3 py-2">
                        <i class="fas fa-check-circle me-1"></i> Match
                      </span>`;
        break;
      case 'Mismatch':
        statusBadge = `<span class="badge rounded-pill bg-danger-subtle text-danger px-3 py-2">
                        <i class="fas fa-exclamation-circle me-1"></i> Mismatch
                      </span>`;
        break;
      case 'Model Not Found':
        statusBadge = `<span class="badge rounded-pill bg-warning-subtle text-warning px-3 py-2">
                        <i class="fas fa-question-circle me-1"></i> Not Found
                      </span>`;
        break;
      case 'Price Format Error':
        statusBadge = `<span class="badge rounded-pill bg-danger-subtle text-danger px-3 py-2">
                        <i class="fas fa-exclamation-triangle me-1"></i> Error
                      </span>`;
        break;
      default:
        statusBadge = `<span class="badge rounded-pill bg-secondary-subtle text-secondary px-3 py-2">
                        <i class="fas fa-info-circle me-1"></i> ${item.status}
                      </span>`;
    }
    
    html += `
      <tr class="border-bottom">
        <td class="px-4 py-3 align-middle">
          <div class="d-flex align-items-center">
            <i class="fas fa-barcode me-2 text-muted"></i>
            <strong>${item.model}</strong>
          </div>
        </td>
        <td class="px-4 py-3 align-middle text-muted small">${descOutput}</td>
        <td class="px-4 py-3 align-middle text-end">$${parseFloat(item.po_price).toFixed(2)}</td>
        <td class="px-4 py-3 align-middle text-end">${item.book_price ? '$' + parseFloat(item.book_price).toFixed(2) : '-'}</td>
        <td class="px-4 py-3 align-middle text-end ${priceCompareClass}">
          <strong>${priceDifference}</strong>
        </td>
        <td class="px-4 py-3 align-middle text-center">
          ${statusBadge}
        </td>
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
    
    <!-- Email report section -->
    <div class="card border-0 rounded-4 overflow-hidden shadow-sm">
      <div class="card-header border-0 bg-white py-3 px-4">
        <div class="d-flex justify-content-between align-items-center">
          <div class="d-flex align-items-center">
            <div class="rounded-circle d-flex align-items-center justify-content-center me-3" 
              style="background-color: var(--light-green); width: 32px; height: 32px;">
              <i class="fas fa-envelope" style="color: var(--primary-green);"></i>
            </div>
            <h6 class="fw-semibold mb-0">Email Report</h6>
          </div>
          
          <button class="btn btn-primary btn-sm px-3 py-2 d-flex align-items-center" id="copy-btn">
            <i class="fas fa-copy me-2"></i> Copy to Clipboard
          </button>
        </div>
      </div>
      
      <div class="card-body p-4">
        <div class="bg-light rounded-3 p-2 mb-3">
          <textarea class="form-control border-0 shadow-none bg-light font-monospace" 
                    id="email-report" rows="10" readonly 
                    style="resize: none;">${data.email_report}</textarea>
        </div>
        
        <div class="d-flex align-items-center">
          <div class="bg-light rounded-circle p-2 d-flex me-3">
            <i class="fas fa-info-circle text-muted"></i>
          </div>
          <span class="small text-muted">This report can be shared with your team or customer service department.</span>
        </div>
      </div>
    </div>
  `;
  
  // Add the HTML to the container
  container.innerHTML = html;
  
  // Add the event listener after a short delay to ensure DOM is ready
  setTimeout(() => {
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
  }, 100);
}
