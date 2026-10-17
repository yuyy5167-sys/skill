import fs from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';
import {renderStill} from '@remotion/renderer';
import {loadConfig,openRender} from './common.mjs';
import {cueTime,transformAt} from '../../src/manga-animation/model.ts';
const c=await loadConfig(),dest=path.resolve('tmp/manga-animation/review');await fs.mkdir(dest,{recursive:true});
const {serveUrl,browser,composition}=await openRender(c),frames=new Set(),hold=c.fps/c.poseHz;
for(const p of c.panels){
 const add=t=>frames.add(Math.min(p.startFrame+p.frames-1,p.startFrame+Math.max(0,Math.round(cueTime(t,c.poseHz)*c.fps))));
 add(0);add(p.seconds-1/c.poseHz);
 for(const part of p.parts)for(const k of part.keys)add(k.at);
 for(const d of p.dialogues){add(d.at-1/c.poseHz);add(d.at);add(d.at+d.readSeconds);}
}
try{
 const thumbnails=[];
 for(const frame of [...frames].sort((a,b)=>a-b)){
  const output=path.join(dest,`frame-${String(frame).padStart(6,'0')}.png`);
  await renderStill({serveUrl,composition,puppeteerInstance:browser,frame,output,imageFormat:'png'});
  thumbnails.push(await sharp(output).resize(384,216,{fit:'contain',background:'#eee'}).png().toBuffer());
 }
 for(let offset=0;offset<thumbnails.length;offset+=24){
  const batch=thumbnails.slice(offset,offset+24);
  await sharp({create:{width:1536,height:Math.ceil(batch.length/4)*216,channels:3,background:'#eee'}}).composite(batch.map((input,i)=>({input,left:i%4*384,top:Math.floor(i/4)*216}))).png().toFile(path.join(dest,`sheet-${offset/24+1}.png`));
 }
 let movingFrame;
 for(const p of c.panels){
  for(let tick=0;tick<p.frames/hold-1;tick++){
   if(p.parts.some(part=>{const a=transformAt(part,tick/c.poseHz),b=transformAt(part,(tick+1)/c.poseHz);return Math.abs(a.dx-b.dx)+Math.abs(a.dy-b.dy)+Math.abs(a.angle-b.angle)>1e-7;})){movingFrame=p.startFrame+tick*hold;break;}
  }
  if(movingFrame!==undefined)break;
 }
 const start=movingFrame??c.panels[0].startFrame,holdFiles=[];
 for(const frame of [start,start+hold-1,start+hold].filter(f=>f<c.frames)){
  const output=path.join(dest,`hold-${frame}.png`);await renderStill({serveUrl,composition,puppeteerInstance:browser,frame,output,imageFormat:'png'});holdFiles.push(await sharp(output).raw().toBuffer());
 }
 const samePose=holdFiles.length>=2&&holdFiles[0].equals(holdFiles[1]);
 if(!samePose)throw new Error('Frames within one pose differ before video compression');
 const report={reviewFrames:[...frames].sort((a,b)=>a-b),poseHoldPassed:samePose,nextPoseChanges:holdFiles.length===3&&!holdFiles[0].equals(holdFiles[2]),movingFrame: movingFrame??null,visualInspection:'not performed by this script',audioListening:'not performed by this script'};
 await fs.writeFile(path.join(dest,'review.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}finally{await browser.close({silent:true});}
