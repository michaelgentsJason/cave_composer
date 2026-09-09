"""Check geometry, camera registration, paper exports and interactive controls."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from pypdf import PdfReader
from playwright.sync_api import sync_playwright

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.verify_cave_showcase import verify


def main(folder):
    folder=Path(folder).resolve()
    report=verify(folder,plate_size=(7200,3600))
    registration=json.loads((folder/'views/registered_views.json').read_text())
    views=registration['views']
    assert len(views)==12
    assert len({v['route'] for v in views})==5
    assert len({hashlib.sha256((folder/v['image']).read_bytes()).hexdigest() for v in views})==12
    panels=[v['plate_panel'] for v in views]
    assert len({tuple(p) for p in panels})==12
    for x,y,w,h in panels:assert x>=0 and y>=0 and x+w<=1 and y+h<=1
    pdf=PdfReader(folder/'figures/cave_showcase.pdf')
    assert len(pdf.pages)==1
    box=pdf.pages[0].mediabox
    assert np.isclose(float(box.width)/float(box.height),2)
    text=pdf.pages[0].extract_text()
    assert '10 m' in text
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto((folder/'index.html').as_uri())
        page.wait_for_function("[...document.querySelectorAll('img')].filter(e=>e.id!=='full').every(e=>e.complete&&e.naturalWidth>0)")
        assert page.locator('.pin').count()==12
        for v in views:
            page.locator('.pin').nth(v['id']-1).click()
            assert v['title'] in page.locator('#title').inner_text()
            assert page.locator('#hero').get_attribute('src')==v['image']
        page.locator('#hero').click();assert page.locator('#viewer').is_visible()
        page.keyboard.press('Escape');assert not page.locator('#viewer').is_visible()
        page.keyboard.press('ArrowRight');assert page.locator('#hero').get_attribute('src')==views[0]['image']
        page.screenshot(path=str(folder/'browser_desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not errors,errors
        browser.close()
    report.update(distinct_images=12,covered_routes=5,pdf_pages=1,plate_resolution=[7200,3600],
        browser_errors=errors,browser_checks=['All images load offline','12 map buttons match images',
            'Modal and keyboard navigation','Mobile width'],
        scope='Registered synthetic render showcase; not a navigation policy or calibration experiment')
    (folder/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',default='outputs/cave_showcase_hard_v02')
    main(parser.parse_args().folder)
