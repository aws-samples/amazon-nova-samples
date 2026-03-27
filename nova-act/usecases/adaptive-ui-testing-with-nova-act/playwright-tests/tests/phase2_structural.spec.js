import { test, expect } from '@playwright/test';

test.describe('Phase 2: Student Registration (v1.5 Structural Changes)', () => {
  
  test('should fill and submit student form with new selectors', async ({ page }) => {
    await page.goto('http://localhost:8000/#student');
    
    // Wait for form to be visible
    await expect(page.locator('#student-form')).toBeVisible();
    
    // THESE SELECTORS CHANGED - Test will fail with old selectors
    // Old: #student-id → New: #student-id-input
    // Old: #save-btn → New: #submit-student-btn
    // Old: #success-message → New: #confirmation-msg
    
    // Fill form with NEW v1.5 selectors
    await page.fill('#student-id-input', 'S999');  // CHANGED
    await page.fill('#first-name', 'Jane');
    await page.fill('#last-name', 'Doe');
    await page.selectOption('#major', 'CS');
    await page.fill('#enrollment-date', '2026-01-15');
    
    // Submit form with NEW button selector
    await page.click('#submit-student-btn');  // CHANGED
    
    // Verify success message with NEW selector
    await expect(page.locator('#confirmation-msg')).toBeVisible();  // CHANGED
  });
});
