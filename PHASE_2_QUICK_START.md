# Phase 2: Quick Start Guide

## Testing the Implemented Features

### Prerequisites

1. **Start the Enhanced Cognee databases:**
```bash
cd "C:\Users\vince\Projects\AI Agents\enhanced-cognee"
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d
```

2. **Start the Dashboard API:**
```bash
cd "C:\Users\vince\Projects\AI Agents\enhanced-cognee"
python dashboard/dashboard_api.py
```

3. **Start the Next.js Dashboard:**
```bash
cd "C:\Users\vince\Projects\AI Agents\enhanced-cognee\dashboard\nextjs-dashboard"
npm run dev
```

4. **Open in Browser:**
```
http://localhost:3000/memories
```

---

## Feature Testing Checklist

### 1. Memory List with Infinite Scroll ✅

**Test Steps:**
- [ ] Navigate to `/memories`
- [ ] Verify memories load (skeleton should show first)
- [ ] Scroll to bottom - should auto-load more memories
- [ ] Click refresh button - should reload with animation
- [ ] Toggle between list/grid view - layout changes
- [ ] Type in search box - results filter after 300ms delay
- [ ] Click "X" to clear search
- [ ] Click "Filters" button - filter panel expands
- [ ] Select memory type - results update instantly
- [ ] Click "Clear All Filters" - all filters reset

**Expected Results:**
- Smooth infinite scroll loading
- No page reloads
- Filter indicator dot appears when filters active
- Results count updates correctly

---

### 2. Memory Detail View ✅

**Test Steps:**
- [ ] From memory list, click on any memory card
- [ ] Verify detail page loads with skeleton first
- [ ] Check all metadata badges display correctly
- [ ] Verify content displays with proper formatting
- [ ] Check "Copy" button next to memory ID works
- [ ] Click "Export" button - should download Markdown file
- [ ] Click "Edit" button - navigates to edit (404 expected, not implemented)
- [ ] Click "Delete" button - confirmation dialog appears
- [ ] Click breadcrumb "Memories" - returns to list

**Expected Results:**
- All memory data displays correctly
- Related memories section shows if applicable
- Exported file contains memory content
- Navigation works smoothly

---

### 3. Batch Operations ✅

**Test Steps:**
- [ ] From memory list, click checkbox on 2-3 memories
- [ ] Verify batch actions toolbar appears
- [ ] Check selection count displays correctly
- [ ] Click "Select All" - all memories selected
- [ ] Click "Deselect All" - all memories deselected
- [ ] Re-select some memories
- [ ] Click "Export" button (logs to console, TODO)
- [ ] Click "Delete" button - confirmation appears
- [ ] Click "Clear Selection" - toolbar disappears

**Expected Results:**
- Selected memories have ring border and left accent bar
- Toolbar appears/disappears smoothly
- Selection persists across page loads
- Batch actions work on selected items only

---

### 4. Search Functionality ✅

**Test Steps:**
- [ ] Navigate to `/search` (if implemented) or use search in memories page
- [ ] Type query in search box
- [ ] Wait 300ms - results should appear
- [ ] Verify result count displays
- [ ] Clear search - recent searches appear
- [ ] Click a recent search - searches again
- [ ] Click a suggested search - searches that term
- [ ] Click on a result - navigates to detail page

**Expected Results:**
- Search debounces properly
- Results update smoothly
- Search history persists across sessions
- Recent searches display correctly

---

### 5. Filter Persistence ✅

**Test Steps:**
- [ ] Apply some filters (type, concept, agent)
- [ ] Refresh page (F5)
- [ ] Verify filters persist after reload
- [ ] Check URL contains query parameters
- [ ] Copy URL and open in new tab
- [ ] Verify filters apply in new tab
- [ ] Clear all filters
- [ ] Refresh page - filters still cleared

**Expected Results:**
- Filters persist via localStorage
- URL syncs correctly
- Shareable URLs work

---

### 6. Export Functionality ✅

**Test Steps:**
- [ ] From memory list, apply filters to get subset
- [ ] Select some memories
- [ ] Click "Export" in batch toolbar
- [ ] Verify file downloads (check Downloads folder)
- [ ] Open downloaded file - verify format is correct
- [ ] From memory detail page, click "Export"
- [ ] Verify single memory exports correctly

**Expected Formats:**
- JSON: Structured data with metadata
- CSV: Tabular format, readable in Excel
- Markdown: Formatted text document

---

### 7. Responsive Design ✅

**Test Steps:**
- [ ] Open browser DevTools (F12)
- [ ] Enable device toolbar
- [ ] Test mobile view (375px width):
  - [ ] Grid view changes to single column
  - [ ] Filters stack vertically
  - [ ] Toolbar adapts to mobile
- [ ] Test tablet view (768px width):
  - [ ] Grid view shows 2 columns
  - [ ] Filters adjust layout
- [ ] Test desktop view (>1024px):
  - [ ] Full layout visible
  - [ ] All features accessible

**Expected Results:**
- Smooth transitions between breakpoints
- All features work on mobile
- Touch targets are large enough (44x44px)

---

### 8. Keyboard Navigation ✅

**Test Steps:**
- [ ] Press `Tab` - focus moves through interactive elements
- [ ] Press `Enter` on focused memory - opens detail
- [ ] Press `Escape` in search - clears search
- [ ] Use arrow keys in dropdowns
- [ ] Verify focus indicators are visible

**Expected Results:**
- All features accessible via keyboard
- Focus order is logical
- Focus indicators clearly visible

---

## Known Limitations (What Won't Work Yet)

### 1. Add Memory Modal ❌
**Status:** Not implemented
**Workaround:** Use backend API directly

### 2. Edit Memory Modal ❌
**Status:** Not implemented
**Workaround:** N/A

### 3. Delete Functionality ⚠️
**Status:** Frontend ready, backend endpoint missing
**Expected:** 404 error when trying to delete
**Fix:** Add DELETE endpoint to backend API

### 4. Update Functionality ⚠️
**Status:** Frontend ready, backend endpoint missing
**Expected:** 404 error when trying to update
**Fix:** Add PATCH endpoint to backend API

### 5. Toast Notifications ⚠️
**Status:** Hook implemented, UI component missing
**Expected:** No visual feedback for some actions
**Fix:** Create Toast UI component

---

## Debugging Tips

### Console Logs
- Open browser DevTools (F12)
- Check Console tab for errors
- All "TODO" comments indicate incomplete features

### Network Requests
- Open Network tab in DevTools
- Look for failed API calls (red status)
- Check response payloads

### React Query Devtools
- Install React Query Devtools browser extension
- Click on React Query icon in browser
- Inspect query cache, mutations, state

### Zustand Devtools
- Zustand state is logged to console
- Access via: `window.__ZUSTAND_STORES__`

---

## Performance Testing

### Load Testing
- Try loading 1000+ memories
- Scroll through entire list
- Check for jank or stuttering
- Monitor memory usage in DevTools

### Search Performance
- Type rapidly in search box
- Verify debounce prevents excessive API calls
- Check search results appear within 500ms

### Filter Performance
- Apply multiple filters simultaneously
- Verify results update instantly (<100ms)
- Check for UI lag

---

## Accessibility Testing

### Screen Reader
- Enable NVDA (Windows) or VoiceOver (Mac)
- Navigate through memories list
- Verify all elements are announced
- Check ARIA labels are descriptive

### Keyboard Only
- Unplug mouse
- Navigate using Tab and arrow keys
- Verify all features accessible
- Check focus management in modals

### High Contrast Mode
- Enable Windows high contrast mode
- Verify all elements visible
- Check color contrast meets WCAG AA

---

## Next Steps After Testing

1. **Report Issues:**
   - Document any bugs found
   - Note improvements needed
   - Suggest UX enhancements

2. **Prepare for Phase 3:**
   - Implement Add/Edit Memory Modals
   - Create Toast UI Component
   - Add backend API endpoints (PATCH, DELETE)
   - Write unit tests

3. **Code Review:**
   - Review TypeScript types
   - Check for any `any` types (should be none)
   - Verify accessibility compliance
   - Ensure responsive design works

---

## Troubleshooting

### Issue: Memories not loading
**Solution:**
- Check backend API is running
- Verify database containers are up
- Check browser console for errors
- Verify API URL in environment variables

### Issue: Infinite scroll not working
**Solution:**
- Check if browser window is tall enough to scroll
- Try zooming out (Ctrl + -)
- Check console for JavaScript errors
- Verify API returns correct pagination

### Issue: Filters not persisting
**Solution:**
- Check localStorage is enabled
- Clear browser cache and retry
- Check browser console for storage errors
- Verify Zustand persist middleware working

### Issue: Export not downloading
**Solution:**
- Check browser download permissions
- Try different browser
- Check console for errors
- Verify export utility functions are correct

---

**Happy Testing!**

Report any issues to the development team or create GitHub issues.
