/**
 * Sample data templates for the website.
 * This file contains examples that users can use as reference when creating their price books.
 */

// Sample Excel structure for price books
const samplePriceBookStructure = {
  headers: ["Model Number", "Correct Base Price"],
  rows: [
    ["ABC123", "299.99"],
    ["XYZ456", "149.50"],
    ["PROD789", "199.00"]
  ]
};

// Function to create a sample Excel file
function createSampleExcel() {
  // This is just a reference function 
  // In a real implementation, this would generate a downloadable Excel file
  console.log("Sample structure for Excel file:", samplePriceBookStructure);
  alert("To create a proper price book Excel file, make sure to include column headers exactly as: 'Model Number' and 'Correct Base Price'");
}