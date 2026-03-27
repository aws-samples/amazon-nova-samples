import { test, expect } from '@playwright/test';

test.describe('Phase 1: Student Registration (v1.0)', () => {
  
  test('should fill and submit student form', async ({ page }) => {
    await page.goto('http://localhost:8000/#student');
    
    // Wait for form to be visible
    await expect(page.locator('#student-form')).toBeVisible();
    
    // Fill form with v1.0 selectors
    await page.fill('#first-name', 'Jane');
    await page.fill('#last-name', 'Doe');
    await page.fill('#student-id', 'S999');
    await page.selectOption('#major', 'CS');
    await page.fill('#enrollment-date', '2026-01-15');
    
    // Submit form
    await page.click('#save-btn');
    
    // Verify success message
    await expect(page.locator('#success-message')).toBeVisible();
  });
});
