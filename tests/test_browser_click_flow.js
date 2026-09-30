// Browser click event and navigation prevention verification
const fs = require('fs');
const path = require('path');

const htmlContent = fs.readFileSync(path.join(__dirname, '../frontend/index.html'), 'utf8');

// 1. Verify all button tags in HTML have explicit type="button" or type="submit"
const buttonRegex = /<button[\s\S]*?>/gi;
const buttons = htmlContent.match(buttonRegex) || [];
let missingType = 0;
let submitButtons = 0;
let buttonTypes = 0;

buttons.forEach((b, idx) => {
  if (!b.includes('type=')) {
    console.error(`Button #${idx} missing type attribute:`, b);
    missingType++;
  } else if (b.includes('type="submit"')) {
    submitButtons++;
  } else if (b.includes('type="button"')) {
    buttonTypes++;
  }
});

console.log(`HTML Button Audit: ${buttons.length} total buttons.`);
console.log(`- type="button": ${buttonTypes}`);
console.log(`- type="submit": ${submitButtons} (only for modal forms)`);
console.log(`- missing type: ${missingType}`);

if (missingType > 0) {
  process.exit(1);
}

// 2. Verify all preset scenario buttons have type="button"
const scenarioBtns = htmlContent.match(/<button[^>]*class="[^"]*btn-scenario[^"]*"[^>]*>/gi) || [];
console.log(`\nScenario buttons found: ${scenarioBtns.length}`);
scenarioBtns.forEach(btn => {
  if (!btn.includes('type="button"')) {
    console.error('Scenario button missing type="button":', btn);
    process.exit(1);
  }
});
console.log('✓ All scenario buttons have explicit type="button"');

// 3. Verify quick suggestion chip buttons have type="button"
const chipBtns = htmlContent.match(/<button[^>]*class="[^"]*chip[^"]*"[^>]*>/gi) || [];
console.log(`Chip buttons found: ${chipBtns.length}`);
chipBtns.forEach(btn => {
  if (!btn.includes('type="button"')) {
    console.error('Chip button missing type="button":', btn);
    process.exit(1);
  }
});
console.log('✓ All preset chip buttons have explicit type="button"');

// 4. Verify Approval buttons have type="button"
['btnApprovePlan', 'btnRejectPlan', 'btnWorkspaceRun', 'btnDashboardRun', 'btnDemoMode'].forEach(id => {
  const match = htmlContent.match(new RegExp(`<button[^>]*id="${id}"[^>]*>`, 'i'));
  if (!match || !match[0].includes('type="button"')) {
    console.error(`Action button ${id} missing type="button"!`, match);
    process.exit(1);
  }
  console.log(`✓ Action button #${id} has type="button"`);
});

// 5. Verify app.js click handlers invoke e.preventDefault()
const jsContent = fs.readFileSync(path.join(__dirname, '../frontend/app.js'), 'utf8');

const handlersToCheck = [
  { name: 'Dashboard Run Button', pattern: /dashBtn\.addEventListener\("click",\s*\(e\)\s*=>\s*\{[\s\S]*?e\.preventDefault\(\)/ },
  { name: 'Preset Chips', pattern: /chip\.addEventListener\("click",\s*\(e\)\s*=>\s*\{[\s\S]*?e\.preventDefault\(\)/ },
  { name: 'Workspace Run Button', pattern: /workBtn\.addEventListener\("click",\s*\(e\)\s*=>\s*\{[\s\S]*?e\.preventDefault\(\)/ },
  { name: 'Approve Plan Button', pattern: /getElementById\("btnApprovePlan"\)\?\.addEventListener\("click",\s*\(e\)\s*=>\s*\{[\s\S]*?e\.preventDefault\(\)/ },
  { name: 'Reject Plan Button', pattern: /getElementById\("btnRejectPlan"\)\?\.addEventListener\("click",\s*\(e\)\s*=>\s*\{[\s\S]*?e\.preventDefault\(\)/ },
  { name: 'Scenario Preset Buttons', pattern: /btn\.addEventListener\("click",\s*\(e\)\s*=>\s*\{[\s\S]*?e\.preventDefault\(\)/ },
  { name: 'Demo Mode Button', pattern: /getElementById\("btnDemoMode"\)\?\.addEventListener\("click",\s*\(e\)\s*=>\s*\{[\s\S]*?e\.preventDefault\(\)/ },
  { name: 'Navigation Tabs', pattern: /tab\.addEventListener\("click",\s*\(e\)\s*=>\s*\{[\s\S]*?e\.preventDefault\(\)/ }
];

console.log('\nChecking app.js event listeners for e.preventDefault():');
handlersToCheck.forEach(h => {
  if (!h.pattern.test(jsContent)) {
    console.error(`❌ ${h.name} is missing e.preventDefault() in its click handler!`);
    process.exit(1);
  }
  console.log(`✓ ${h.name} properly calls e.preventDefault()`);
});

console.log('\nAll browser click flow assertions PASSED!');
