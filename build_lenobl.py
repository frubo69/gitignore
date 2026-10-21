from __future__ import annotations
import io, os, re, math, time
from pathlib import Path
from urllib.parse import urljoin
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H=1600,900
OUT=Path('output'); OUT.mkdir(exist_ok=True)
CACHE=Path('cache'); CACHE.mkdir(exist_ok=True)
CREAM=(244,240,230); DEEP=(13,43,42); TEAL=(114,185,174); GOLD=(202,158,78); INK=(24,35,34); WHITE=(250,250,246); MUTED=(118,128,123)
S=requests.Session(); S.headers.update({'User-Agent':'Mozilla/5.0 LenoblastPresentation/1.0 educational'})
USED=set(); CREDITS=[]
FONT_SANS='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; FONT_SANS_B='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'; FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'; FONT_SERIF_B='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'

def font(size,bold=False,serif=False):
 p=FONT_SERIF_B if serif and bold else FONT_SERIF if serif else FONT_SANS_B if bold else FONT_SANS
 return ImageFont.truetype(p,size)
def safe(s): return re.sub(r'[^a-zA-Z0-9_-]+','_',s)[:80]
def download(url,path):
 for k in range(4):
  try:
   r=S.get(url,timeout=35,allow_redirects=True); r.raise_for_status()
   if len(r.content)<8000: raise ValueError('too small')
   im=Image.open(io.BytesIO(r.content)); im.load()
   if im.width<500 or im.height<300: raise ValueError('small image')
   im.convert('RGB').save(path,'JPEG',quality=92); return path
  except Exception:
   if k==3: raise
   time.sleep(2*(k+1))
def commons_photo(query,key):
 path=CACHE/f'{safe(key)}.jpg'
 if path.exists(): return path
 params={'action':'query','generator':'search','gsrsearch':query,'gsrnamespace':6,'gsrlimit':20,'prop':'imageinfo','iiprop':'url|extmetadata','iiurlwidth':1800,'format':'json','formatversion':2}
 bad=('map','plan','coat','arms','flag','logo','diagram','scheme','drawing','painting','engraving','stamp','icon','svg','locator','oblast')
 for attempt in range(3):
  try:
   data=S.get('https://commons.wikimedia.org/w/api.php',params=params,timeout=40).json(); pages=data.get('query',{}).get('pages',[]); pages=sorted(pages,key=lambda x:x.get('index',999))
   for p in pages:
    title=p.get('title',''); low=title.lower()
    if not low.endswith(('.jpg','.jpeg','.png','.webp','.tif','.tiff')) or any(x in low for x in bad): continue
    ii=(p.get('imageinfo') or [{}])[0]; url=ii.get('thumburl') or ii.get('url')
    if not url or url in USED: continue
    try:
     download(url,path); USED.add(url); CREDITS.append((key,title,ii.get('descriptionurl',url))); return path
    except Exception: continue
  except Exception: time.sleep(2)
 url='https://cdn.pixabay.com/photo/2022/06/27/22/12/ladoga-7288392_1280.jpg'; download(url,path); CREDITS.append((key,'Lake Ladoga photograph - Pixabay',url)); return path
def og_photo(page_url,key,query_fallback):
 path=CACHE/f'{safe(key)}.jpg'
 if path.exists(): return path
 try:
  html=S.get(page_url,timeout=30).text; u=None
  for pat in [r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']']:
   m=re.search(pat,html,re.I)
   if m: u=urljoin(page_url,m.group(1)); break
  if u: download(u,path); CREDITS.append((key,f'Official website: {page_url}',page_url)); return path
 except Exception: pass
 return commons_photo(query_fallback,key)
def photo(key,query=None,official=None): return og_photo(official,key,query or key) if official else commons_photo(query or key,key)
def crop(im,box):
 x,y,w,h=box; ratio=w/h; r=im.width/im.height
 if r>ratio: nw=int(im.height*ratio); left=(im.width-nw)//2; c=im.crop((left,0,left+nw,im.height))
 else: nh=int(im.width/ratio); top=(im.height-nh)//2; c=im.crop((0,top,im.width,top+nh))
 return c.resize((w,h),Image.Resampling.LANCZOS)
def place(canvas,path,box,shade=0,blur=0):
 im=Image.open(path).convert('RGB')
 if blur: im=im.filter(ImageFilter.GaussianBlur(blur))
 im=crop(im,box)
 if shade:
  ov=Image.new('RGBA',im.size,(0,0,0,shade)); im=Image.alpha_composite(im.convert('RGBA'),ov).convert('RGB')
 canvas.paste(im,(box[0],box[1]))
def wrap(draw,text,f,maxw):
 words=text.split(); lines=[]; cur=''
 for wd in words:
  t=(cur+' '+wd).strip()
  if draw.textbbox((0,0),t,font=f)[2]<=maxw: cur=t
  else:
   if cur: lines.append(cur)
   cur=wd
 if cur: lines.append(cur)
 return lines
def txt(draw,xy,text,f,fill,maxw=None,spacing=8,anchor=None):
 x,y=xy; lines=text.split('\n') if maxw is None else sum([wrap(draw,p,f,maxw) or [''] for p in text.split('\n')],[])
 for ln in lines: draw.text((x,y),ln,font=f,fill=fill,anchor=anchor); y+=f.size+spacing
 return y
def label(draw,text,x,y,fill=GOLD): draw.text((x,y),text.upper(),font=font(16,True),fill=fill)
def footer(draw,num,total,dark=False,source=None):
 col=(235,235,225) if dark else (70,83,78); draw.line((70,850,1530,850),fill=col,width=1); draw.text((70,862),'ЛЕНИНГРАДСКАЯ ОБЛАСТЬ / ТУРИСТСКИЕ РЕСУРСЫ',font=font(12),fill=col); draw.text((1530,862),f'{num:02d} / {total:02d}',font=font(12,True),fill=col,anchor='ra')
def new(bg=CREAM): return Image.new('RGB',(W,H),bg)
def cover(title,subtitle,p,tag):
 c=new(); place(c,p,(0,0,W,H),shade=85); d=ImageDraw.Draw(c,'RGBA'); d.rectangle((0,0,590,H),fill=(8,38,37,235)); label(d,tag,70,75,TEAL); d.line((70,120,500,120),fill=TEAL,width=2); y=txt(d,(70,180),title,font(58,True,True),WHITE,450,12); txt(d,(70,y+25),subtitle,font(27),WHITE,440,8); txt(d,(70,735),'Вода • лес • история • инфраструктура',font(18),TEAL,440); return c
def hero(title,subtitle,p,facts=(),tag=''):
 c=new(); place(c,p,(0,0,W,H),shade=95); d=ImageDraw.Draw(c,'RGBA'); label(d,tag,70,65,GOLD); y=txt(d,(70,135),title,font(52,True,True),WHITE,900,10); txt(d,(70,y+20),subtitle,font(25),WHITE,820,8)
 if facts:
  d.rectangle((55,635,1545,815),fill=(7,35,34,205)); x=80; cw=1450//len(facts)
  for i,(a,b) in enumerate(facts): xx=x+i*cw; d.text((xx,665),a,font=font(28,True),fill=TEAL); txt(d,(xx,710),b,font(18),WHITE,cw-35,5)
 return c
def split(title,subtitle,p,bullets,photo_left=True,tag=''):
 c=new(); d=ImageDraw.Draw(c); ib=(0,0,760,H) if photo_left else (840,0,760,H); place(c,p,ib); tx=820 if photo_left else 70; label(d,tag,tx,65,GOLD); y=txt(d,(tx,120),title,font(43,True,True),INK,690,8); txt(d,(tx,y+15),subtitle,font(21),MUTED,680,7); y+=110
 for i,b in enumerate(bullets,1): d.ellipse((tx,y+5,tx+24,y+29),fill=TEAL); d.text((tx+12,y+17),str(i),font=font(12,True),fill=WHITE,anchor='mm'); y=txt(d,(tx+40,y),b,font(20),INK,640,6)+24
 return c
def grid(title,subtitle,items,cols=3,tag='',dark=False):
 c=new(DEEP if dark else CREAM); d=ImageDraw.Draw(c,'RGBA'); fg=WHITE if dark else INK; sub=(200,215,208) if dark else MUTED; label(d,tag,70,55,GOLD); y=txt(d,(70,105),title,font(42,True,True),fg,1450,8); txt(d,(70,y+8),subtitle,font(20),sub,1450,6); rows=math.ceil(len(items)/cols); gap=20; left=70; top=240; totalw=1460; cardw=(totalw-gap*(cols-1))//cols; cardh=(570-gap*(rows-1))//rows
 for i,(name,cap,p) in enumerate(items):
  r=i//cols; cc=i%cols; x=left+cc*(cardw+gap); yy=top+r*(cardh+gap); place(c,p,(x,yy,cardw,cardh-80),shade=20); d.rectangle((x,yy+cardh-80,x+cardw,yy+cardh),fill=(8,38,37,230) if dark else (255,255,250,245)); d.text((x+15,yy+cardh-67),name,font=font(18,True,True),fill=WHITE if dark else INK); txt(d,(x+15,yy+cardh-40),cap,font(13),TEAL if dark else MUTED,cardw-30,3)
 return c
def stats(title,p,stats,tag=''):
 c=new(); d=ImageDraw.Draw(c); place(c,p,(760,0,840,H),shade=10); label(d,tag,70,65,GOLD); y=txt(d,(70,120),title,font(44,True,True),INK,620,8)+60
 for val,cap in stats: d.text((70,y),val,font=font(46,True),fill=DEEP); txt(d,(70,y+55),cap,font(18),MUTED,580,5); y+=140
 return c
def timeline(title,subtitle,items,tag=''):
 c=new(); d=ImageDraw.Draw(c); label(d,tag,70,55,GOLD); y=txt(d,(70,105),title,font(42,True,True),INK,1450,8); txt(d,(70,y+8),subtitle,font(20),MUTED,1450); gap=18; x0=70; top=240; cw=(1460-gap*3)//4
 for i,(name,months,cap,p) in enumerate(items): x=x0+i*(cw+gap); place(c,p,(x,top,cw,330),shade=15); d.rectangle((x,570,x+cw,805),fill=(255,255,250)); d.text((x+18,595),name,font=font(24,True,True),fill=DEEP); d.text((x+18,635),months,font=font(16,True),fill=GOLD); txt(d,(x+18,680),cap,font(15),INK,cw-36,4)
 return c
def sources_slide(title,deck_credits):
 c=new(); d=ImageDraw.Draw(c); label(d,'ИСТОЧНИКИ ФОТОГРАФИЙ',70,55,GOLD); txt(d,(70,105),title,font(42,True,True),INK,1450); y=190; uniq=[]; seen=set()
 for k,t,u in deck_credits:
  if u not in seen: seen.add(u); uniq.append((k,t,u))
 for i,(k,t,u) in enumerate(uniq[:13],1): d.text((70,y),f'{i:02d}',font=font(15,True),fill=TEAL); txt(d,(115,y-2),f'{t} — {u}',font(13),INK,1400,3); y+=47
 txt(d,(70,810),'Использованы документальные фотографии из Wikimedia Commons и открытых официальных сайтов. Карты и схемы — учебные.',font(14),MUTED,1450); return c
def save_pdf(slides,name):
 jpgs=[]
 for i,im in enumerate(slides,1): p=OUT/f'{safe(name)}_{i:02d}.jpg'; im.save(p,'JPEG',quality=91,subsampling=0); jpgs.append(Image.open(p).convert('RGB'))
 pdf=OUT/f'{name}.pdf'; jpgs[0].save(pdf,'PDF',resolution=150.0,save_all=True,append_images=jpgs[1:]); return pdf
P={}
def ph(k,q=None,official=None):
 if k not in P: P[k]=photo(k,q,official)
 return P[k]

start=len(CREDITS); ns=[]
ns.append(cover('ЛЕНИНГРАДСКАЯ\nОБЛАСТЬ','Природные ресурсы',ph('ladoga_cover','Lake Ladoga Leningrad Oblast landscape'),'ЭКСПЕДИЦИОННЫЙ АТЛАС / 01'))
ns.append(stats('Область между морем и озёрами',ph('gulf_aerial','Gulf of Finland coast Leningrad Oblast'),[('83,9 тыс. км²','площадь региона'),('около 2 млн','население'),('Гатчина','административный центр')],'ВСТУПЛЕНИЕ / ГЕОГРАФИЧЕСКИЙ ПРОФИЛЬ'))
ns.append(hero('Большая вода. Тихий лес. Близкий маршрут.','Сочетание морского побережья, озёр и лесов — основа коротких и многодневных поездок.',ph('karelian_landscape','Karelian Isthmus lake landscape'),[('БАЛТИКА','выход к Финскому заливу'),('ЛАДОГА','крупнейшее озеро Европы'),('ЛЕСА И БОЛОТА','экологические маршруты')],'УНИКАЛЬНОЕ ТУРИСТСКОЕ ПРЕДЛОЖЕНИЕ'))
ns.append(grid('Самые выразительные водные ресурсы','Вода задаёт образ региона и формирует разные сценарии отдыха.',[('Ладожское озеро','шхеры, острова, открытая вода',ph('ladoga_islands','Lake Ladoga skerries islands')),('Финский залив','побережья и морские панорамы',ph('gulf_coast','Gulf of Finland coast Russia')),('Вуокса','озёрно-речная система Карельского перешейка',ph('vuoksa','Vuoksa River Leningrad Oblast'))],3,'ВОДНЫЕ РЕСУРСЫ / КРУПНЫЕ ОБЪЕКТЫ'))
ns.append(grid('Реки связывают природные территории','Судоходные артерии, пороги и тихие лесные русла.',[('Нева','выход Ладоги к Финскому заливу',ph('neva','Neva River landscape')),('Свирь','связь Ладоги и Онеги',ph('svir','Svir River landscape')),('Волхов','историческая и энергетическая ось',ph('volkhov','Volkhov River Leningrad Oblast'))],3,'ВОДНЫЕ РЕСУРСЫ / РЕКИ',True))
ns.append(grid('Где какие почвы','Ландшафт и увлажнение определяют почвенный покров.',[('Карельский перешеек','дерново-подзолистые и песчаные',ph('karelian_soil','Karelian Isthmus sandy forest')),('Ижорская возвышенность','дерново-карбонатные почвы',ph('izhora','Izhora Upland landscape')),('Мшинское болото','торфяно-болотные почвы',ph('mshinskoye','Mshinskoye swamp nature reserve'))],3,'ЗЕМЕЛЬНЫЕ И ПОЧВЕННЫЕ РЕСУРСЫ'))
ns.append(split('Лес — не один сплошной массив','Лесные территории различаются породами, влажностью и доступностью.',ph('lindulovskaya','Lindulovskaya Grove forest'),['Карельский перешеек — сосновые и смешанные леса.','Линдуловская роща — исторические лиственничные посадки.','Вепсский лес — крупный природный парк востока области.'],True,'ЛЕСНЫЕ РЕСУРСЫ'))
ns.append(grid('Минеральные ресурсы: привязка к месту','Регион богат прежде всего строительным и химическим сырьём.',[('Гранит','Выборгский район',ph('granite_quarry','granite quarry Vyborg district Russia')),('Фосфориты','Кингисеппский район',ph('phosphorite','phosphorite mining quarry Russia')),('Торф','болотные массивы области',ph('peat','peat extraction Russia'))],3,'НЕДРА / МЕСТОРОЖДЕНИЯ',True))
ns.append(hero('Энергия воды и природного сырья','Речной сток, гидроузлы и лесные ресурсы формируют энергетический потенциал.',ph('volkhov_hpp','Volkhov hydroelectric station'),[('ГИДРОЭНЕРГИЯ','Свирь и Волхов'),('ТОРФ','локальное топливное сырьё'),('БИОМАССА','ресурс лесного комплекса')],'ЭНЕРГЕТИЧЕСКИЕ РЕСУРСЫ'))
ns.append(grid('Растительный мир: лес и редкие виды','Обычные виды формируют ландшафт, редкие требуют охраны.',[('Сосна и ель','основа хвойных лесов',ph('pine_spruce','pine spruce forest Russia')),('Черника и брусника','характерные лесные кустарнички',ph('berries','bilberry lingonberry forest')),('Венерин башмачок','редкий охраняемый вид',ph('orchid','Cypripedium calceolus flower'))],3,'БИОЛОГИЧЕСКИЕ РЕСУРСЫ / ФЛОРА'))
ns.append(grid('Животный мир: видеть, не тревожить','Наблюдение за животными строится на дистанции и правилах охраны.',[('Лось','крупный обитатель лесов',ph('elk','European elk Russia forest')),('Ладожская нерпа','эндемичный подвид Ладоги',ph('seal','Ladoga ringed seal')),('Редкие птицы','скопа, орлан-белохвост и другие виды',ph('osprey','osprey bird Russia'))],3,'БИОЛОГИЧЕСКИЕ РЕСУРСЫ / ФАУНА',True))
ns.append(grid('Охраняемые территории — четыре разных опыта','Режим охраны важнее популярности места.',[('Линдуловская роща','исторический лиственничный лес',ph('lindulovskaya2','Lindulovskaya Grove larch forest')),('Кургальский заказник','побережья, острова и миграции птиц',ph('kurgalsky','Kurgalsky Peninsula nature reserve')),('Вепсский лес','таёжные ландшафты востока',ph('veps','Vepsian Forest nature park')),('Мшинское болото','озёра и торфяные массивы',ph('mshinskoye2','Mshinskoye swamp lake'))],2,'ПРИРОДООХРАННЫЙ ПОТЕНЦИАЛ'))
ns.append(hero('Климат меняет сценарий отдыха','Балтийское влияние смягчает погоду, но ветер, влажность и ледовая обстановка важны круглый год.',ph('gulf_weather','Gulf of Finland rocky coast sunset'),[('ПОБЕРЕЖЬЕ','ветер и морское влияние'),('ВНУТРЕННИЕ РАЙОНЫ','более континентальные черты'),('БЕЛЫЕ НОЧИ','длинный световой день')],'КЛИМАТИЧЕСКИЕ РЕСУРСЫ'))
ns.append(timeline('Когда посещать: календарь сезонов','Пик активных поездок — с конца весны до начала осени.',[('Весна','апрель — май','экскурсии, цветение, высокий уровень воды',ph('spring','spring forest Leningrad Oblast')),('Лето','июнь — август','озёра, побережья, водные маршруты',ph('summer','summer lake Leningrad Oblast')),('Осень','сентябрь — октябрь','грибы, фотомаршруты, золотые леса',ph('autumn','autumn forest Leningrad Oblast')),('Зима','декабрь — март','лыжи, снегоступы, зимние фестивали',ph('winter','winter forest Leningrad Oblast'))],'КЛИМАТ И РЕКРЕАЦИЯ / СЕЗОННОСТЬ'))
ns.append(hero('Большие территории — разная доступность','Размер района не равен времени в пути: важны дороги, переправы и сезон.',ph('road_region','Leningrad Oblast road forest'),[('ПОДПОРОЖСКИЙ','восточные таёжные маршруты'),('ВЫБОРГСКИЙ','побережья и Карельский перешеек'),('БОКСИТОГОРСКИЙ','леса и удалённые озёра'),('ТИХВИНСКИЙ','природа и культурные объекты')],'РЕСУРСЫ ПРОСТРАНСТВА'))
ns.append(grid('Сколько времени закладывать','Время — самостоятельный туристский ресурс.',[('1 день','ближние пригороды и один объект',ph('daytrip','Gatchina park landscape')),('2–3 дня','Выборгский берег или озёрный маршрут',ph('weekend','Vyborg Bay landscape')),('4–5 дней','восток области и несколько природных зон',ph('longtrip','Vepsian Forest landscape'))],3,'РЕСУРСЫ ВРЕМЕНИ / СЦЕНАРИИ ПОЕЗДКИ'))
ns.append(hero('Сильный маршрут строится на сочетании','Вода даёт масштаб, лес — глубину впечатления, сезон и доступ — реалистичность.',ph('nature_final','Lake Ladoga forest coast sunset'),[('ГЛАВНОЕ','связать объекты одной географической зоны'),('СЕЗОН','учитывать воду, лёд и погоду'),('БЕРЕЖНОСТЬ','сохранять сам ресурс')],'ВЫВОД / ТУРИСТСКИЙ ПОТЕНЦИАЛ'))
ns.append(sources_slide('Источники фотографий: природные ресурсы',CREDITS[start:]))
for i,s in enumerate(ns,1): footer(ImageDraw.Draw(s),i,len(ns),dark=(i in [1,3,5,8,9,11,13,15,17]))
save_pdf(ns,'01_Ленинградская_область_Природные_ресурсы_реальные_фото')

start=len(CREDITS); cs=[]
cs.append(cover('ЛЕНИНГРАДСКАЯ\nОБЛАСТЬ','Культурно-исторические ресурсы',ph('vyborg_cover','Vyborg Castle aerial'),'ЭКСПЕДИЦИОННЫЙ АТЛАС / 02'))
cs.append(stats('Наследие разных эпох',ph('staraya_aerial','Staraya Ladoga fortress aerial'),[('IX–XX вв.','широкий исторический диапазон'),('крепости','граница, торговля и оборона'),('дворцы и парки','имперское наследие')],'КУЛЬТУРНЫЙ ПРОФИЛЬ'))
cs.append(split('Старая Ладога','Археология, древняя крепость и память о ранних торговых путях.',ph('staraya','Staraya Ladoga fortress'),['Удалённость от Гатчины: около 150 км.','На осмотр: 2–3 часа.','Объективный признак: подлинный археологический и архитектурный комплекс.','Субъективный образ: «начало древнерусского маршрута».'],True,'ПАМЯТНИК АРХЕОЛОГИИ И ИСТОРИИ'))
cs.append(split('Выборгский замок','Средневековая крепость на острове — главный визуальный символ Выборга.',ph('vyborg_castle','Vyborg Castle Russia'),['Удалённость от Гатчины: около 180 км.','На осмотр: 2–4 часа.','Объективный признак: башня, фортификация, музей.','Субъективный образ: североевропейская атмосфера.'],False,'ПАМЯТНИК АРХИТЕКТУРЫ'))
cs.append(split('Крепость Орешек','Островная крепость у истока Невы и один из ключевых оборонительных объектов региона.',ph('oreshek','Oreshek fortress Shlisselburg'),['Удалённость от Гатчины: около 95 км.','На осмотр: 2–3 часа с переправой.','Объективный признак: крепостные стены и музейная экспозиция.','Субъективный образ: изолированность и драматическая история.'],True,'ПАМЯТНИК ИСТОРИИ'))
cs.append(split('Гатчинский дворец и парк','Парадная архитектура, интерьеры и система пейзажных парков.',ph('gatchina','Gatchina Palace Russia'),['Расположен в административном центре области.','На посещение: 3–5 часов.','Объективный признак: дворцово-парковый ансамбль.','Субъективный образ: имперская торжественность и спокойствие парка.'],False,'ДВОРЦОВО-ПАРКОВЫЙ АНСАМБЛЬ'))
cs.append(split('Парк Монрепо','Скальный пейзажный парк на берегу Выборгского залива.',ph('monrepos','Monrepos Park Vyborg'),['Удалённость от Гатчины: около 185 км.','На прогулку: 2–4 часа.','Объективный признак: природно-архитектурный комплекс.','Субъективный образ: романтический северный пейзаж.'],True,'ЛАНДШАФТНОЕ НАСЛЕДИЕ'))
cs.append(grid('Ещё четыре культурные опоры','Минимум текста — максимум визуального узнавания.',[('Ивангород','крепость на Нарве',ph('ivangorod','Ivangorod Fortress')),('Копорье','средневековые руины',ph('koporye','Koporye fortress')),('Тихвин','монастырь и паломнические маршруты',ph('tikhvin','Tikhvin Assumption Monastery')),('Приоратский дворец','редкая землебитная архитектура',ph('priory','Priory Palace Gatchina'))],2,'ПАМЯТНИКИ АРХИТЕКТУРЫ И ИСТОРИИ'))
cs.append(grid('Нематериальное культурное наследие','Традиция живёт через язык, ремесло, музыку и праздник.',[('Вепсская культура','язык, орнамент и традиционная кухня',ph('veps_culture','Veps people traditional costume')),('Ижорские традиции','песенная культура и местные праздники',ph('izhora_culture','Izhorians traditional costume')),('Ремёсла','ткачество, дерево, керамика',ph('craft','Russian traditional weaving craft'))],3,'НЕМАТЕРИАЛЬНЫЕ РЕСУРСЫ',True))
cs.append(grid('Музеи и документальные памятники','Архивы, предметы и интерьеры превращают историю в рассказ.',[('Выборгский музей','история города и замка',ph('vyborg_museum','Vyborg Castle museum interior')),('Гатчинский музей','дворцовые интерьеры и коллекции',ph('gatchina_interior','Gatchina Palace interior')),('Дорога жизни','документы и мемориальные объекты',ph('road_life','Road of Life museum Leningrad Oblast'))],3,'ДОКУМЕНТАЛЬНЫЕ И МУЗЕЙНЫЕ РЕСУРСЫ'))
cs.append(hero('Объективные и субъективные признаки','Ресурс оценивают не только по возрасту и сохранности, но и по силе впечатления.',ph('cultural_route','Vyborg old town street'),[('ОБЪЕКТИВНО','подлинность, сохранность, доступность'),('СУБЪЕКТИВНО','атмосфера, эмоциональность, уникальность'),('ПРАКТИЧЕСКИ','время, удалённость, режим работы')],'КАК ОЦЕНИВАТЬ КУЛЬТУРНЫЙ РЕСУРС'))
cs.append(grid('Три маршрута для знакомства','Лучше объединять близкие объекты, чем собирать случайный перечень.',[('Северо-запад','Выборг + Монрепо',ph('route_vyborg','Vyborg aerial city')),('Ладожская ось','Старая Ладога + Шлиссельбург',ph('route_ladoga','Lake Ladoga fortress landscape')),('Южное направление','Гатчина + Копорье + Ивангород',ph('route_south','Ivangorod Narva fortresses'))],3,'МАРШРУТНАЯ ЛОГИКА'))
cs.append(hero('Наследие работает вместе с ландшафтом','Сильнейшие объекты Ленинградской области невозможно отделить от воды, скал, парков и приграничной истории.',ph('cultural_final','Vyborg Castle sunset'),[('4+ ПРИМЕРА','объекты разных эпох'),('НЕМАТЕРИАЛЬНОЕ','культуры малых народов'),('ДОСТУПНОСТЬ','маршруты из Санкт-Петербурга')],'ВЫВОД / УНИКАЛЬНОЕ ПРЕДЛОЖЕНИЕ'))
cs.append(sources_slide('Источники фотографий: культурно-исторические ресурсы',CREDITS[start:]))
for i,s in enumerate(cs,1): footer(ImageDraw.Draw(s),i,len(cs),dark=(i in [1,9,11,13]))
save_pdf(cs,'02_Ленинградская_область_Культурно_исторические_ресурсы_реальные_фото')

start=len(CREDITS); ss=[]
ss.append(cover('ЛЕНИНГРАДСКАЯ\nОБЛАСТЬ','Социально-экономические ресурсы',ph('pulkovo_cover','Pulkovo airport terminal'),'ЭКСПЕДИЦИОННЫЙ АТЛАС / 03'))
ss.append(hero('Инфраструктура превращает объект в поездку','Транспорт, размещение, питание, информация и кадры связывают природные и культурные ресурсы.',ph('transport_mix','Lastochka train Russia station'),[('ТРАНСПОРТ','авиа, железная дорога, автотрассы'),('РАЗМЕЩЕНИЕ','городские и загородные форматы'),('ПИТАНИЕ','локальная и историческая кухня')],'СОЦИАЛЬНО-ЭКОНОМИЧЕСКИЙ ПРОФИЛЬ'))
ss.append(split('Аэропорт Пулково','Главный авиационный вход в агломерацию и отправная точка для маршрутов по области.',ph('pulkovo','Pulkovo airport terminal exterior'),['До Гатчины — около 30 км.','Доступны такси, автобусы и пересадки на железную дорогу.','Для удалённых районов требуется дополнительный наземный трансфер.'],True,'ТРАНСПОРТ / АЭРОПОРТ'))
ss.append(grid('Транспорт: четыре опорных системы','Выбор транспорта зависит от направления и глубины маршрута.',[('Железная дорога','Выборг, Гатчина, Тихвин, Волхов',ph('train','Lastochka train Finland Station')),('Автомобильные трассы','М10, М11, А181 и региональные дороги',ph('motorway','M11 motorway Russia')),('Водный транспорт','Ладога, Нева, залив и сезонная навигация',ph('boat','Lake Ladoga passenger boat')),('Порт Усть-Луга','крупный транспортно-логистический узел',ph('ust_luga','Ust-Luga port aerial'))],2,'МАТЕРИАЛЬНЫЕ РЕСУРСЫ / ТРАНСПОРТ'))
ss.append(grid('Четыре варианта размещения','Город, курорт и природа — разные сценарии одной области.',[('Курорт «Игора»','активный отдых и круглогодичная инфраструктура',ph('igora','Igora resort Leningrad Oblast',official='https://igora.ru/')),('«Охта Парк»','курорт рядом с Санкт-Петербургом',ph('ohta','Okhta Park resort',official='https://ohtapark.ru/')),('«Лесная рапсодия»','загородный отель у озера',ph('rhapsody','Forest Rhapsody hotel',official='https://forest-rhapsody.ru/')),('Отель «Дружба»','городское размещение в Выборге',ph('druzhba','Hotel Druzhba Vyborg'))],2,'ИНФРАСТРУКТУРА РАЗМЕЩЕНИЯ'))
ss.append(grid('Как выбирать размещение','Не только цена: важны сезон, транспорт и сценарий поездки.',[('Городской отель','экскурсии и пешая доступность',ph('city_hotel','Vyborg hotel exterior')),('Загородный курорт','спорт, SPA, семейный отдых',ph('resort','Leningrad Oblast resort hotel')),('Эко-размещение','тишина и близость к природе',ph('eco_hotel','eco hotel forest Russia'))],3,'РАЗМЕЩЕНИЕ / КРИТЕРИИ ВЫБОРА',True))
ss.append(grid('Четыре ресторана и кафе','Заведения дополняют маршрут локальной и исторической атмосферой.',[('«Средневековая таверна»','Выборг: тематическая кухня',ph('taverna','medieval tavern Vyborg restaurant',official='https://taverna-vyborg.ru/')),('«Эспиля»','Выборг: городской ресторан',ph('espilya','Espilya restaurant Vyborg',official='https://espilya.ru/')),('«Царская усадьба»','Гатчина: ресторанный комплекс',ph('tsar','Tsarskaya Usadba Gatchina restaurant')),('«Круглая башня»','Выборг: ресторан в историческом здании',ph('round_tower','Round Tower Vyborg restaurant'))],2,'ИНФРАСТРУКТУРА ПИТАНИЯ'))
ss.append(split('Питание как часть маршрута','Кафе и рестораны работают лучше, когда связаны с темой территории.',ph('food','Russian northern cuisine restaurant'),['Выборг — средневековая и североевропейская стилистика.','Гатчина — дворцово-парковый маршрут.','Ладожское направление — рыба и локальные продукты.','В высокий сезон столики и группы бронируют заранее.'],False,'ПИТАНИЕ / ТУРИСТСКИЙ ОПЫТ'))
ss.append(hero('Трудовые ресурсы','Качество поездки зависит от водителей, гидов, сотрудников гостиниц, музеев и природных территорий.',ph('guide','tour guide group Russia museum'),[('КВАЛИФИКАЦИЯ','знание территории и безопасность'),('СЕЗОННОСТЬ','нагрузка меняется по месяцам'),('ОБУЧЕНИЕ','сервис, языки, цифровые навыки')],'ТРУДОВЫЕ РЕСУРСЫ'))
ss.append(hero('Информация и управление','Навигация, сайты, расписания, бронирование и координация участников делают сложный маршрут понятным.',ph('info','tourist information center Russia'),[('ИНФОРМАЦИЯ','карты, базы, расписания'),('УПРАВЛЕНИЕ','планирование потоков'),('КОММУНИКАЦИЯ','единый образ территории')],'ИНФОРМАЦИОННЫЕ И УПРАВЛЕНЧЕСКИЕ РЕСУРСЫ'))
ss.append(timeline('Сезонность инфраструктуры','Часть объектов работает круглый год, часть зависит от навигации и погоды.',[('Зима','декабрь — март','курорты, лыжи, зимние программы',ph('infra_winter','ski resort Leningrad Oblast')),('Весна','апрель — май','экскурсии и короткие поездки',ph('infra_spring','Gatchina park spring')),('Лето','июнь — август','пик размещения и водных маршрутов',ph('infra_summer','Vyborg summer tourism')),('Осень','сентябрь — ноябрь','фестивали и спокойный экскурсионный сезон',ph('infra_autumn','Vyborg autumn'))],'СЕЗОННОСТЬ / НАГРУЗКА'))
ss.append(hero('Главное преимущество — шаговая доступность разнообразия','Аэропорт, железная дорога и трассы позволяют связать крепости, дворцы, озёра и леса в короткие маршруты.',ph('social_final','Vyborg city aerial sunset'),[('БЛИЗОСТЬ','к Санкт-Петербургу'),('РАЗНООБРАЗИЕ','город + природа + история'),('ПОТЕНЦИАЛ','для круглогодичного туризма')],'ВЫВОД / ТУРИСТСКИЙ ПОТЕНЦИАЛ'))
ss.append(sources_slide('Источники фотографий: социально-экономические ресурсы',CREDITS[start:]))
for i,s in enumerate(ss,1): footer(ImageDraw.Draw(s),i,len(ss),dark=(i in [1,2,6,9,10,12]))
save_pdf(ss,'03_Ленинградская_область_Социально_экономические_ресурсы_реальные_фото')
print('Generated PDFs')
for p in OUT.glob('*.pdf'): print(p,p.stat().st_size)
