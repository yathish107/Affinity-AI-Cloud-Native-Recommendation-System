"""Run against a live local stack: python frontend/browser-tests/test_ui.py."""
from playwright.sync_api import sync_playwright
import os
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1280,'height':800})
    page.goto(os.getenv('UI_URL','http://localhost:8080'))
    page.get_by_role('heading',name='Find what fits you.').wait_for()
    page.locator('#products .card').first.wait_for()
    page.locator('#search').fill('Laptop')
    assert page.locator('#products .card').count()==1
    page.locator('#products button').first.click()
    page.wait_for_function("document.getElementById('message').textContent.includes('recorded')")
    page.get_by_role('button',name='Your Activity').click()
    page.locator('#historyRows .history-row').first.wait_for()
    page.route('**/api/system',lambda route:route.fulfill(status=500,body='{}',content_type='application/json'))
    page.get_by_role('button',name='System Health').click()
    page.wait_for_function("document.getElementById('message').textContent.includes('Request failed')")
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    browser.close()
