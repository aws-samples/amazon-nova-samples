import { test, expect } from '@playwright/test';

test.describe('Phase 3: Student Registration (v2.0 New Features)', () => {
  
  test('should fill and submit student form with new fields', async ({ page }) => {
    await page.goto('http://localhost:8000/#student');
    
    // Wait for form to be visible
    await expect(page.locator('#student-form')).toBeVisible();
    
    // NEW FIELDS ADDED - Test needs updates for email and GPA
    
    // Fill form with v2.0 selectors and NEW fields
    await page.fill('#student-id-input', 'S999');
    await page.fill('#first-name', 'Jane');
    await page.fill('#last-name', 'Doe');
    await page.fill('#student-email', 'jane.doe@university.edu');  // NEW FIELD
    await page.selectOption('#major', 'CS');
    await page.fill('#student-gpa', '3.8');  // NEW FIELD
    await page.fill('#enrollment-date', '2026-01-15');
    
    // Submit form
    await page.click('#submit-student-btn');
    
    // Verify success message
    await expect(page.locator('#confirmation-msg')).toBeVisible();
  });
});
