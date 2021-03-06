import logging
import re
import scrapy
import redis
from ..items import StoryItem, LinksItem, IndexItem
from tianyadata.models import Index, Story
from django.db import connection

'''
增量 对比回复时间与上次的回复时间，判断是否更新
首页的链接和links表中比较如果他存在与links表说明不是全新的帖子，index只更新时间，帖子从后面开始抓取5页比较
否则是全新的帖子，从最后一页开始全部抓取
'''
'''
redis_db = redis.Redis(host='YOUIP', port=6379, db=1)  # 连接redis
redis_data_dict = "tianya_url"
'''


class TianyaSpider(scrapy.Spider):
    name = "tianya"
    allowed_domains = ['tianya.cn']
    root_url = 'http://bbs.tianya.cn'
    start_urls = ['http://bbs.tianya.cn/list-16-1.shtml', ]
    '''初始请求'''

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse_lasttime, dont_filter=True)
            yield scrapy.Request(url=url, callback=self.parse, dont_filter=True)

    with open(r"/home/yqq/enviro/env/scrapy_django_tianya2/tianya/last_runtime.txt") as f:
        last_time = f.readline()  # 上次抓取时间

    '''只抓取回复时间比抓取时间早的帖子'''

    def parse(self, response):
        reply_timelist = response.xpath('//div[@id="main"]/div/table/tbody/tr/td[5]/@title').extract()  # 回复时间列表
        story_author = response.xpath(
                        '//div[@id="main"]/div/table/tbody/tr/td[2]/a//text()').extract()  # 全部author的list
        count = -1
        for col in response.xpath('//div[@id="main"]/div/table/tbody/tr/td[1]'):  # 选取主页可见标题
            count += 1
            indexitem = IndexItem()
            if reply_timelist[count] > self.last_time: # 比较回复时间和爬取时间抓取时间新的
                story_title = "".join(col.xpath('a//text()').extract()).strip().replace('\n', '')  # 选取标题
                indexitem["story_title"] = story_title
                urltemp = "".join(col.xpath('a/@href').extract()).strip()
                story_link_main = self.root_url + urltemp
                indexitem["story_link_main"] = story_link_main  # 帖子主链接
                indexitem["story_author"] = story_author[count]  # 作者
                story_replytime_new = reply_timelist[count]  # 时间
                story_replytime = response.xpath(
                    '//*[@id="main"]/div[7]/table/tbody/tr/td[5]/@title').extract()  # 回复时间  # 全部reply_time的list
                indexitem["story_replytime"] = story_replytime[count]  # 帖子的回复时间
                # 数据库查 可能会耗时久
                cond = Index.objects.filter(story_link_main=story_link_main).all()  # 从数据库中查询是否有改url 没有的话为[]
                if len(cond) == 0:  # 当这里是[]时 即url为全新的
                    indexitem.save()
                    logging.info(indexitem)
                    yield scrapy.Request(url=story_link_main, callback=self.parse_allpage, dont_filter=True,
                                meta={"flag": "new"})
                else:  # URL已经出现过
                    Index.objects.filter(story_link_main=story_link_main).update(
                        story_replytime=story_replytime_new)  # 只更新时间
                    yield scrapy.Request(url=story_link_main, callback=self.parse_allpage, dont_filter=True,
                                                meta={"flag": "old"})          
            else:
                break
        if reply_timelist[len(reply_timelist) - 1] > self.last_time:  # 如果该页的最后一个回复时间大于上次爬取时间说明下页还有待爬取的数据
            tmp = response.xpath(
                '//div[@id="main"]/div/div[@class="links"]/a[@rel]/@href').extract_first()  # 下一页 str
            if tmp is not None:
                index_nextpage = self.root_url + tmp  # 主页下一页
                yield scrapy.Request(url=index_nextpage, callback=self.parse, dont_filter=True)
                logging.info(index_nextpage)

    def parse_lasttime(self, response):
        lasttime_xpath = response.xpath(
            '//*[@id="main"]/div[7]/table/tbody/tr/td[5]/@title').extract()  # 回复时间
        lasttime = lasttime_xpath[1]  # 最大回复时间
        with open(r"/home/yqq/enviro/env/scrapy_django_tianya2/tianya/last_runtime.txt", "w+") as f:
            f.write(lasttime)

    '''拼接全部页码，从最后一页开始抓取并且去重'''

    def parse_allpage(self, response):
        flag = response.meta["flag"]
        if flag == 'new':
            pagelist = response.xpath('//div[@id="post_head"]/div/div/form/a/@href').extract()  # 取到说明是多页
            if not pagelist:  # 没有多页这里是[] 说明只有一页
                yield scrapy.Request(url=response.url, callback=self.parse_detail)
            else:  # pagelist不是[]说明多页
                last_page_temp = pagelist[len(pagelist) - 2]  # 最后一页链接 倒序切片有时候报错越界如 /post-16-1699084-22.shtml
                url_head = last_page_temp.split('-')[0:-1]  # url头
                pages = int(last_page_temp.split('-')[-1].split('.')[0])  # 最后一页页码数
                for i in range(pages, 0, -1):  # 倒序去遍历url
                    link = self.root_url + '-'.join(url_head).strip() + '-' + str(i) + '.shtml'  # 倒序拼接出全部url
                    # '''redis去重比较'''
                    # if redis_db.hexists(redis_data_dict, link) == 0:  # 如果这个url的key不在field里面说明新页面
                    yield scrapy.Request(url=link, callback=self.parse_detail)  # priority=i,
        if flag == 'old':
            pagelist = response.xpath('//div[@id="post_head"]/div/div/form/a/@href').extract()  # 取到说明是多页
            if not pagelist:  # 没有多页这里是[] 说明只有一页
                # if redis_db.hexists(redis_data_dict, response.url) == 0:  # 如果这个url的key不在field里面说明新页面
                yield scrapy.Request(url=response.url, callback=self.parse_detail)
            else:  # pagelist不是[]说明多页
                last_page_temp = pagelist[len(pagelist) - 2]  # 最后一页链接 倒序切片有时候报错越界如 /post-16-1699084-22.shtml
                url_head = last_page_temp.split('-')[0:-1]  # url头
                pages = int(last_page_temp.split('-')[-1].split('.')[0])  # 最后一页页码数
                for i in range(pages, pages - 6, -1):  # 倒序去遍历后5个url
                    link = self.root_url + '-'.join(url_head).strip() + '-' + str(i) + '.shtml'  # 倒序拼接出全部url
                    yield scrapy.Request(url=link, callback=self.parse_detail)  # priority=i,

    '''解析每页的具体内容'''

    def parse_detail(self, response):
        # 帖子的作者 若此是空字符串说明是问答贴，drop
        author = "".join(
            response.xpath('//div[@id="post_head"]/div/div/span/a/@uname').extract()).strip()
        story_title = "".join(
            response.xpath('//div/h1//span//text()').extract()).strip()  # 帖子标题
        # 帖子发布时间
        story_posttime = "".join(
            response.xpath('//div[@id="post_head"]/div/div/span[2]//text()').re('\d\S.*')).strip()
        # authorid用于标识楼主的内容
        authorid = "".join(response.xpath('//div[@id="post_head"]/div/div/span/a/@uid').extract())
        page = (response.url.split('-')[-1].split('.')[0])  # 现在str类型 标识帖子页码
        story_mark = "-".join(response.url.split('-')[0:-1]).strip()
        if len(authorid) > 0:
            contenttmp = response.xpath(
                '//div/div[@*={}]//div[starts-with(@class,"bbs-content")]'.format(authorid)).extract()
            if len(contenttmp) > 0:
                for i in range(len(contenttmp), 0, -1):  # 倒序遍历这一页的章节
                    story_link = response.url + '-part{}'.format(i)
                    '''直接从数据库查速度还行，如果太慢再想其他方法'''
                    cond2 = Story.objects.filter(story_link=story_link).all()
                    if len(cond2) != 0:  # 某个章节已经存在 跳出循环
                        break
                    else:
                        linkitem = LinksItem()
                        linkitem["links"] = response.url  # 把url存到links表 重复的页面更新会存不进去
                        logging.info(linkitem)
                        linkitem.save()
                        storyitem = StoryItem()
                        story_order = int(page) * 1000 + i  # 这里记得改page*10000+order
                        storyitem["story_author"] = author
                        storyitem["story_author_id"] = authorid
                        storyitem["story_title"] = story_title
                        storyitem["story_posttime"] = story_posttime
                        storyitem["story_order"] = story_order  # 帖子顺序
                        storyitem["story_mark"] = story_mark  # 帖子标识
                        storyitem["story_link"] = story_link  # 帖子唯一链接
                        col_no_br = contenttmp[i - 1].replace(r'<br>', '\n')  # 替换<br>
                        content = re.sub(r'</?\w+[^>]*>', '', col_no_br)  # 去掉html标签
                        content_len = "".join(content).strip().replace('\t', '')
                        if len(content_len) < 20:
                            storyitem["story_content"] = "Useless"  # 内容字符过少视为无用内容
                        else:
                            storyitem["story_content"] = content  # 帖子每章节的内容
                            yield storyitem
                            logging.info(storyitem)
