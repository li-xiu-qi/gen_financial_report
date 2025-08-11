#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web搜索服务
"""

import asyncio
import json
import time
import threading
import argparse
import logging
from datetime import datetime
from urllib.parse import unquote
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn
from typing import Dict, List, Optional, Any

# 第三方库
from playwright.async_api import async_playwright, Page, Browser
import aiohttp
from concurrent.futures import ThreadPoolExecutor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Cache:
    """简单的内存缓存实现"""
    
    def __init__(self):
        self._data = {}
        self._timers = {}
        self._cache_ttl = 5 * 60  # 5分钟缓存
    
    def has(self, key: str) -> bool:
        return key in self._data
    
    def get(self, key: str) -> Any:
        if key in self._timers:
            self._timers[key].cancel()
        self._set_expiry(key)
        return self._data.get(key)
    
    def set(self, key: str, value: Any) -> Any:
        if key in self._timers:
            self._timers[key].cancel()
        self._data[key] = value
        self._set_expiry(key)
        return value
    
    def _set_expiry(self, key: str):
        def expire():
            self._data.pop(key, None)
            self._timers.pop(key, None)
        
        timer = threading.Timer(self._cache_ttl, expire)
        timer.start()
        self._timers[key] = timer
    
    async def use(self, key: str, search_func):
        """如果有缓存直接返回，否则执行搜索函数并缓存结果"""
        if self.has(key):
            return self.get(key)
        
        try:
            result = await search_func(key)
            if not isinstance(result, Exception):
                self.set(key, result)
            return result
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {"error": str(e), "type": "search_error"}


class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            devtools=False,
            slow_mo=200,
            args=['--no-startup-window'],
            ignore_default_args=['--enable-automation', '--disable-blink-features=AutomationControlled']
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def new_page(self, url: str = None, selector: str = None) -> Page:
        """创建新页面并可选择性导航到URL和等待选择器"""
        page = await self.browser.new_page()
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        })
        
        if url:
            await page.goto(url)
        
        if selector:
            try:
                if isinstance(selector, list):
                    selector = ','.join(selector)
                await page.wait_for_selector(selector, timeout=30000)
            except Exception as e:
                logger.warning(f"等待选择器失败: {e}")
        
        # 设置3分钟后自动关闭
        async def auto_close():
            await asyncio.sleep(180)  # 3分钟
            try:
                await page.close()
            except:
                pass
        
        asyncio.create_task(auto_close())
        return page


class SearchHandlers:
    """搜索处理器集合"""
    
    def __init__(self):
        self.cache = Cache()
    
    async def help(self, params: Dict) -> str:
        """返回所有可用接口的帮助信息"""
        handlers = [
            "sohu - 搜狐新闻搜索",
            "gov - 政府政策搜索", 
            "iwencai - 问财网信息搜索",
            "cninfo - 巨潮资讯公告查询",
            "bing - 必应搜索",
            "whpj - 中国银行外汇牌价",
            "10jqka - 同花顺基本面数据",
            "goto - 通用网页抓取"
        ]
        return "\n".join(handlers)
    
    async def sohu(self, params: Dict) -> List[Dict]:
        """搜狐新闻搜索接口"""
        query = params.get('query', '')
        url = f"https://search.sohu.com/?keyword={query}"
        
        async def search_sohu(cache_key):
            async with BrowserManager() as browser_mgr:
                page = await browser_mgr.new_page(url, 'div[data-spm=news-list] div[class^=cards-small]')
                
                # 获取搜索结果列表
                results = await page.evaluate("""
                    () => {
                        const list = [];
                        for (const el of document.querySelectorAll('div[data-spm=news-list] div[class^=cards-small]')) {
                            const a = el.querySelector('h4 a,.cards-content-title a');
                            if (a) {
                                list.push({
                                    url: a.href,
                                    title: a.textContent?.trim(),
                                    abstract: el.querySelector('.plain-content-desc,.cards-content-right-desc')?.textContent?.trim()
                                });
                            }
                        }
                        return list;
                    }
                """)
                
                # 获取每篇文章的内容
                await asyncio.sleep(0.6)
                for item in results:
                    if item['url']:
                        logger.info(f"加载: {item['title']}")
                        try:
                            await page.goto(item['url'])
                            await page.wait_for_selector('div[data-spm=content] .article', timeout=30000)
                            content = await page.evaluate("""
                                () => document.querySelector('div[data-spm=content] .article')?.textContent?.trim()
                            """)
                            item['content'] = content
                            await asyncio.sleep(0.6)
                        except Exception as e:
                            logger.warning(f"获取内容失败: {e}")
                            continue
                
                return results
        
        return await self.cache.use(url, search_sohu)
    
    async def gov(self, params: Dict) -> List[Dict]:
        """政府政策搜索接口"""
        query = params.get('query', '')
        url = f"https://www.gov.cn/search/zhengce/?t=zhengce&q={query}&timetype=&mintime=&maxtime=&sort=score&sortType=1&searchfield=&pcodeJiguan=&childtype=&subchildtype=&tsbq=&pubtimeyear=&puborg=&pcodeYear=&pcodeNum=&filetype=&p=0&n=5&inpro=&sug_t=zhengce"
        
        async def search_gov(cache_key):
            async with BrowserManager() as browser_mgr:
                page = await browser_mgr.new_page(url, 'div.dys_middle_result_content .middle_result_con')
                
                await asyncio.sleep(0.2)
                
                # 获取搜索结果
                results = await page.evaluate("""
                    () => {
                        const list = [];
                        for (const ul of document.querySelectorAll('div.dys_middle_result_content .middle_result_con')) {
                            for (const li of ul.children) {
                                const a = li.querySelector('a');
                                if (a) {
                                    list.push({
                                        type: ul.getAttribute('index'),
                                        title: li.textContent.trim(),
                                        url: a.href
                                    });
                                }
                            }
                        }
                        return list;
                    }
                """)
                
                # 获取每个政策的详细内容
                await asyncio.sleep(0.6)
                for item in results:
                    if item['url']:
                        logger.info(f"加载: {item['title']}")
                        try:
                            await page.goto(item['url'])
                            await page.wait_for_selector('div.pages_content', timeout=30000)
                            content = await page.evaluate("""
                                () => document.querySelector('div.pages_content')?.textContent?.trim()
                            """)
                            item['content'] = content
                            await asyncio.sleep(0.6)
                        except Exception as e:
                            logger.warning(f"获取内容失败: {e}")
                            continue
                
                return results
        
        return await self.cache.use(url, search_gov)
    
    async def iwencai(self, params: Dict) -> List[Dict]:
        """问财网信息搜索接口"""
        query = params.get('query', '')
        url = f"https://www.iwencai.com/unifiedwap/inforesult?w={query}&querytype=info&tab="
        
        async def search_iwencai(cache_key):
            async with BrowserManager() as browser_mgr:
                page = await browser_mgr.new_page(url, 'div.info-result-list')
                
                results = await page.evaluate("""
                    () => {
                        const list = [];
                        for (const el of document.querySelectorAll('div.info-result-list .info-item.info-item-web')) {
                            const a = el.querySelector('a[rel=noopener]');
                            const p = el.querySelector('p.desc');
                            const title = a?.textContent?.trim();
                            
                            if (title && p) {
                                list.push({
                                    title,
                                    url: a.href,
                                    abstract: p.textContent?.trim()
                                });
                            }
                        }
                        return list;
                    }
                """)
                
                return results
        
        return await self.cache.use(url, search_iwencai)
    
    async def bing(self, params: Dict) -> List[Dict]:
        """必应搜索接口"""
        query = params.get('query', '')
        total = int(params.get('total', 5))
        cn = params.get('cn', 'false').lower() == 'true'
        
        search_param = '' if cn else '&ensearch=1'
        url = f"https://cn.bing.com/search?scope=web&q={query}{search_param}"
        
        async def search_bing(cache_key):
            async with BrowserManager() as browser_mgr:
                accept_selectors = [
                    'button:has-text("Accept")', 'button:has-text("接受")',
                    '#bnp_btn_accept', '#bnp_btn_prefer'
                ]
                page = await browser_mgr.new_page(url, ['form[action="/search"] input'] + accept_selectors)
                
                # 处理接受按钮
                for selector in accept_selectors:
                    try:
                        if await page.is_visible(selector):
                            await page.click(selector)
                            await asyncio.sleep(0.2)
                            break
                    except:
                        continue
                
                # 选择语言
                try:
                    await page.click('#est_cn' if cn else '#est_en')
                    await page.wait_for_timeout(200)
                    await page.wait_for_load_state('domcontentloaded')
                except:
                    pass
                
                # 等待搜索结果
                try:
                    await page.wait_for_selector('#b_results', timeout=1000)
                except:
                    pass
                
                async def read_results():
                    return await page.evaluate("""
                        () => {
                            const list = [];
                            for (const el of document.querySelectorAll('#b_results li.b_algo')) {
                                const a = el.querySelector('h2 a, h3 a');
                                if (!a) continue;
                                
                                const url = a.href;
                                if (!url.startsWith('http') || 
                                    ['bing.com/search', 'bing.cn/search', 'microsoft.com/en-us/bing'].some(t => url.includes(t))) {
                                    continue;
                                }
                                
                                list.push({
                                    url: a.href,
                                    title: a.textContent?.trim(),
                                    abstract: el.querySelector('.b_caption,.b_lineclamp2,.b_lineclamp3')?.textContent?.trim()
                                });
                            }
                            return list;
                        }
                    """)
                
                # 获取第一页结果
                await page.keyboard.press('End')
                results = await read_results()
                
                # 翻页获取更多结果
                page_num = 1
                while len(results) < total:
                    page_num += 1
                    await page.keyboard.press('End')
                    
                    next_page_selector = f'.b_widePag[aria-label$=" {page_num}"]'
                    if not await page.is_visible(next_page_selector):
                        break
                    
                    await page.click(next_page_selector)
                    await page.wait_for_load_state('domcontentloaded')
                    
                    try:
                        await page.wait_for_selector('#b_results', timeout=1000)
                    except:
                        pass
                    
                    new_results = await read_results()
                    results.extend(new_results)
                
                return results[:total]
        
        return await self.cache.use(url, search_bing)
    
    async def whpj(self, params: Dict) -> List[Dict]:
        """中国银行外汇牌价接口"""
        cache_key = str(int(time.time() / 3600))  # 按小时缓存
        
        async def get_whpj(cache_key):
            async with BrowserManager() as browser_mgr:
                results = []
                
                for i in range(1, 6):
                    if i > 1:
                        await asyncio.sleep(0.6)
                    
                    url = f"https://www.boc.cn/sourcedb/whpj/index_{i}.html"
                    page = await browser_mgr.new_page(url)
                    await page.wait_for_load_state('load')
                    await page.wait_for_selector('tr.odd', timeout=1000)
                    
                    page_results = await page.evaluate("""
                        () => {
                            const list = [];
                            const cols = Array.from(document.querySelectorAll('tr.odd th')).map(th => th.textContent.trim());
                            
                            for (const tr of document.querySelectorAll('tr.odd:has(td)')) {
                                const cells = Array.from(tr.querySelectorAll('th,td')).map(cell => cell.textContent.trim());
                                const row = {};
                                cells.forEach((cell, index) => {
                                    if (cols[index]) {
                                        row[cols[index]] = cell;
                                    }
                                });
                                list.push(row);
                            }
                            
                            return list;
                        }
                    """)
                    
                    results.extend(page_results)
                
                return results
        
        return await self.cache.use(cache_key, get_whpj)
    
    async def goto(self, params: Dict) -> Dict:
        """通用网页抓取接口"""
        query = params.get('query', '')
        selector = params.get('selector', '')
        full = params.get('full', 'false').lower() == 'true'
        
        url = unquote(query)
        cache_key = query + str(full)
        
        async def fetch_page(cache_key):
            async with BrowserManager() as browser_mgr:
                page = await browser_mgr.new_page()
                
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=5000)
                    await page.wait_for_selector('body', timeout=1000)
                except Exception as e:
                    if 'Timeout' not in str(e):
                        return 408
                
                await page.keyboard.press('End')
                
                if selector:
                    try:
                        await page.wait_for_selector(selector, timeout=2000)
                    except:
                        pass
                
                result = await page.evaluate("""
                    (full) => {
                        const body = document.body.cloneNode(true);
                        body.querySelectorAll('script,style').forEach(el => el.remove());
                        return {
                            html: body.innerHTML.trim(),
                            title: document.title.trim()
                        };
                    }
                """, full)
                
                result['url'] = page.url
                return result
        
        return await self.cache.use(cache_key, fetch_page)


# FastAPI实现
app = FastAPI()
handlers = SearchHandlers()

@app.get("/help")
async def help_api():
    result = await handlers.help({})
    return PlainTextResponse(result)

@app.get("/sohu")
async def sohu_api(query: str = Query(...)):
    result = await handlers.sohu({"query": query})
    if isinstance(result, dict) and "error" in result:
        return JSONResponse(result, status_code=500)
    return JSONResponse(result)

@app.get("/gov")
async def gov_api(query: str = Query(...)):
    result = await handlers.gov({"query": query})
    if isinstance(result, dict) and "error" in result:
        return JSONResponse(result, status_code=500)
    return JSONResponse(result)

@app.get("/iwencai")
async def iwencai_api(query: str = Query(...)):
    result = await handlers.iwencai({"query": query})
    if isinstance(result, dict) and "error" in result:
        return JSONResponse(result, status_code=500)
    return JSONResponse(result)

@app.get("/bing")
async def bing_api(query: str = Query(...), total: int = 5, cn: bool = False):
    result = await handlers.bing({"query": query, "total": total, "cn": str(cn).lower()})
    if isinstance(result, dict) and "error" in result:
        return JSONResponse(result, status_code=500)
    return JSONResponse(result)

@app.get("/whpj")
async def whpj_api():
    result = await handlers.whpj({})
    if isinstance(result, dict) and "error" in result:
        return JSONResponse(result, status_code=500)
    return JSONResponse(result)

@app.get("/goto")
async def goto_api(query: str = Query(...), selector: str = '', full: bool = False):
    result = await handlers.goto({"query": query, "selector": selector, "full": str(full).lower()})
    if isinstance(result, dict) and "error" in result:
        return JSONResponse(result, status_code=500)
    return JSONResponse(result)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Web搜索服务')
    parser.add_argument('--port', type=int, default=30002, help='服务端口号')
    args = parser.parse_args()
    logger.info(f"FastAPI服务器启动在端口: {args.port}")
    uvicorn.run("search:app", host="0.0.0.0", port=args.port, reload=False)


if __name__ == '__main__':
    main()
