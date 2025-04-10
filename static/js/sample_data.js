/**
 * Creates a sample Excel file for demonstrating price book format
 */
function createSampleExcel() {
    // This functionality would require a server-side component to generate an actual Excel file
    // For our purposes, we'll just show a modal with example data
    const excelModal = new bootstrap.Modal(document.getElementById('excelFormatModal'));
    excelModal.show();
}

// Event listener for the sample data button
document.addEventListener('DOMContentLoaded', function() {
    const sampleBtn = document.getElementById('show-sample-btn');
    if (sampleBtn) {
        sampleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            createSampleExcel();
        });
    }
});