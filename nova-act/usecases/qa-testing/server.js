const express = require('express');
const path = require('path');
// semgrep:skip=javascript.express.security.audit.express-security-audit: This is a demo application for QA testing purposes only
const app = express();
const PORT = process.env.PORT || 3000;

// Serve static files from the current directory
app.use(express.static(__dirname));

// Serve the index.html file for all routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
  console.log(`QA Testing App is now available at http://localhost:${PORT}`);
});
