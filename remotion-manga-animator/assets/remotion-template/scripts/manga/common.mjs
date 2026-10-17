import fs from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';
import {bundle} from '@remotion/bundler';
import {openBrowser,selectComposition} from '@remotion/renderer';
import {resolveConfig} from '../../src/manga-animation/model.ts';
export const root=process.cwd();
export const publicPath=file=>path.join(root,'public',file);
export const rawConfig=()=>fs.readFile(path.join(root,'src/manga-animation/manga.config.json'),'utf8').then(JSON.parse);
export async function loadConfig(checkAssets=true){
 const c=resolveConfig(await rawConfig());
 if(checkAssets){
  for(const p of c.panels){
   const images=[p.image,p.baseImage,...(p.layers??[]).map(l=>l.image),...(p.dialogues??[]).map(d=>d.cover.image)].filter(Boolean);
   for(const file of new Set(images)){
    const m=await sharp(publicPath(file)).metadata();
    if(m.width!==p.size[0]||m.height!==p.size[1])throw new Error(`${p.id}: ${file} dimensions ${m.width}x${m.height} differ from size ${p.size.join('x')}`);
   }
  }
  for(const a of c.audio??[])await fs.access(publicPath(a.src));
 }
 return c;
}
export async function openRender(c){
 const serveUrl=await bundle({entryPoint:path.join(root,'src/manga-animation/index.tsx'),outDir:path.join(root,'tmp/manga-animation/bundle')});
 const browser=await openBrowser('chrome',{browserExecutable:process.env.REMOTION_BROWSER_EXECUTABLE||undefined});
 try{
  const composition=await selectComposition({serveUrl,id:c.id,puppeteerInstance:browser});
  return {serveUrl,browser,composition};
 }catch(e){await browser.close({silent:true});throw e;}
}
