# Debug Steps for Context Buttons

## Step 1: Reload the Extension

1. Open Chrome and go to: `chrome://extensions/`
2. Find "GitHub RAG Agent" 
3. Click the **Reload** button (circular arrow icon)
4. Close any open extension popups

## Step 2: Test on GitHub

1. Navigate to any GitHub repository, for example:
   - `https://github.com/karpathy/nanochat`
   - Or any other public repo

2. Click the extension icon in the Chrome toolbar

3. **Check the console for debug messages**:
   - Right-click anywhere in the popup
   - Select "Inspect"
   - Look at the Console tab
   - You should see messages like:
     ```
     Initialized elements:
     addToContextBtn: <button id="add-to-context-btn">
     contextInfo: <div id="context-info">
     ```

## Step 3: Load a Repository

1. If the repo isn't loaded, click "Load Repository"
2. Wait for it to complete
3. Watch the console - you should see:
   ```
   showChatInterface called - currentRepoName: nanochat
   About to call updateContextInfoVisibility
   updateContextInfoVisibility - isLoaded: true currentRepoName: nanochat contextInfo: [object]
   Showing context info section
   ```

## Step 4: Verify Buttons are Visible

After the repository is loaded:

1. The chat interface should appear
2. **Look for the context section** with light blue background
3. You should see two buttons:
   - `✓ Add Selection`
   - `✕ Clear Context`

## Step 5: Test Adding Context

1. **Go back to the GitHub page** (click outside the popup)
2. **Select some code** on the GitHub page (any text)
3. **Click the extension icon again**
4. **Click "✓ Add Selection"** button
5. You should see:
   - Button briefly changes to "✓ Added!"
   - A line appears: "✂️ Code selected (...preview...)"

## Troubleshooting

### If buttons still don't appear:

#### Check 1: Is context-info visible in the DOM?
In the Inspector (while inspecting the popup):
1. Go to Elements tab
2. Find: `<div id="context-info" class="context-info">`
3. Check if it has class `hidden`
   - ✅ Should NOT have `hidden` class when repo is loaded
   - ❌ If it has `hidden`, the section is not showing

#### Check 2: Console Errors
Look for any red errors in the console that might indicate:
- Elements not found
- API connection issues
- JavaScript errors

#### Check 3: Backend is Running
```bash
curl http://localhost:8000/health
```
Should return: `{"status":"healthy"}`

#### Check 4: Current File State
Run this in the popup console (while inspecting):
```javascript
console.log('isLoaded:', isLoaded);
console.log('currentRepoName:', currentRepoName);
console.log('contextInfo element:', contextInfo);
console.log('contextInfo hidden?', contextInfo?.classList.contains('hidden'));
console.log('addToContextBtn:', addToContextBtn);
```

### Expected Output (when working):
```javascript
isLoaded: true
currentRepoName: "nanochat"
contextInfo element: <div id="context-info" class="context-info">...</div>
contextInfo hidden? false
addToContextBtn: <button id="add-to-context-btn" class="btn-secondary">...</button>
```

## Visual Check

When everything is working, the extension should look like this:

```
┌────────────────────────────────────┐
│ GitHub RAG Agent                   │
│ Repository: nanochat               │  ← Repo name visible
│                                    │
│ ┌────────────────────────────────┐ │
│ │ [✓ Add Selection]              │ │  ← These buttons should be visible
│ │ [✕ Clear Context]              │ │
│ └────────────────────────────────┘ │  ← Light blue background box
│                                    │
│ 👋 Hi! I'm your GitHub RAG Agent   │  ← Chat interface below
│                                    │
│ [Ask a question about the code...] │
└────────────────────────────────────┘
```

## If Still Not Working

1. **Try a different browser profile** to rule out conflicts
2. **Check file permissions** - make sure all files are readable
3. **Completely remove and re-add** the extension
4. **Share the console output** - copy any errors you see

## Quick Test Script

Paste this in the popup console to check everything:

```javascript
console.log('=== CONTEXT BUTTONS DEBUG ===');
console.log('State:', { isLoaded, currentRepoName, currentFilePath, selectedCode });
console.log('Elements:', { 
  contextInfo: !!contextInfo, 
  addToContextBtn: !!addToContextBtn,
  clearSelectionBtn: !!clearSelectionBtn 
});
console.log('Visibility:', {
  'contextInfo hidden': contextInfo?.classList.contains('hidden'),
  'contextInfo display': window.getComputedStyle(contextInfo).display
});
console.log('=====================');
```
