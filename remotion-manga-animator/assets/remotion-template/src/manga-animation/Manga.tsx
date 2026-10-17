import React,{useEffect,useLayoutEffect,useRef,useState} from 'react';
import {AbsoluteFill,Audio,Sequence,cancelRender,continueRender,delayRender,staticFile,useCurrentFrame} from 'remotion';
import type {ResolvedConfig,ResolvedPanel,Point} from './types';
import {poseTime,transformAt} from './model';
import {makeMesh,drawMesh} from './mesh';
const points=(p:Point[])=>p.map(v=>v.join(',')).join(' ');
const href=(file:string)=>staticFile(file);

const PanelScene:React.FC<{panel:ResolvedPanel;config:ResolvedConfig;seconds:number}>=({panel,config,seconds})=>{
 const canvas=useRef<HTMLCanvasElement>(null),mesh=useRef<ReturnType<typeof makeMesh>|null>(null);
 const [handle]=useState(()=>delayRender(`Loading panel ${panel.id}`));
 const [images,setImages]=useState<Record<string,HTMLImageElement>|null>(null);
 const [w,h]=panel.size,margin=config.margin??Math.round(Math.min(config.width,config.height)*.055);
 const scale=Math.min((config.width-2*margin)/w,(config.height-2*margin)/h),sw=Math.round(w*scale),sh=Math.round(h*scale);
 useEffect(()=>{
  let active=true;
  const files=[panel.image,panel.baseImage,...(panel.layers??[]).map(l=>l.image),...(panel.dialogues??[]).map(d=>d.cover.image)].filter((s):s is string=>Boolean(s));
  Promise.all([...new Set(files)].map(file=>new Promise<[string,HTMLImageElement]>((resolve,reject)=>{const img=new Image();img.onload=()=>resolve([file,img]);img.onerror=()=>reject(new Error(`Missing or unreadable image: ${file}`));img.src=href(file);})))
   .then(items=>{if(active)setImages(Object.fromEntries(items));}).catch(e=>{if(active)cancelRender(e);});
  return ()=>{active=false;};
 },[panel]);
 useLayoutEffect(()=>{
  if(!images)return;
  try{if(panel.mode==='mesh'){mesh.current=makeMesh(canvas.current!,panel,images[panel.image]);drawMesh(mesh.current,panel,seconds);}continueRender(handle);}
  catch(e){cancelRender(e instanceof Error?e:new Error(String(e)));}
  return ()=>{mesh.current?.dispose();mesh.current=null;};
 },[images,panel,handle]);
 useLayoutEffect(()=>{if(mesh.current)drawMesh(mesh.current,panel,seconds);},[panel,seconds]);
 const prefix=panel.id;
 return <div style={{position:'absolute',left:(config.width-sw)/2,top:(config.height-sh)/2,width:sw,height:sh,overflow:'hidden'}}>
  {panel.mode==='mesh'?<canvas ref={canvas} width={sw} height={sh} style={{display:'block',width:sw,height:sh}}/>:null}
  <svg width={sw} height={sh} viewBox={`0 0 ${w} ${h}`} style={{position:panel.mode==='mesh'?'absolute':'relative',inset:0,display:'block'}}>
   <defs>
    {(panel.layers??[]).map((l,i)=>l.polygon?<clipPath key={i} id={`${prefix}-l-${i}`}><polygon points={points(l.polygon)}/></clipPath>:null)}
    {(panel.dialogues??[]).map((d,i)=><clipPath key={i} id={`${prefix}-d-${i}`}><polygon points={points(d.mask)}/></clipPath>)}
   </defs>
   {panel.mode==='layers'?<>
    <image href={href(panel.baseImage!)} width={w} height={h}/>
    {panel.layers!.map((l,i)=>{
     const part=panel.parts.find(p=>p.id===l.part),v=part?transformAt(part,seconds):{dx:0,dy:0,angle:0};
     const transform=part?`translate(${v.dx} ${v.dy}) rotate(${v.angle} ${part.pivot[0]} ${part.pivot[1]})`:undefined;
     return <g key={l.id} transform={transform}><image href={href(l.image)} width={w} height={h} clipPath={l.polygon?`url(#${prefix}-l-${i})`:undefined}/></g>;
    })}
   </>:null}
   {(panel.dialogues??[]).map((d,i)=>seconds<d.at?<g key={d.id} clipPath={`url(#${prefix}-d-${i})`}>
    {d.cover.image?<image href={href(d.cover.image)} width={w} height={h}/>:<rect width={w} height={h} fill={d.cover.color}/>}
   </g>:null)}
  </svg>
 </div>;
};

export const Manga:React.FC<{config:ResolvedConfig}>=({config})=>{
 const frame=useCurrentFrame(),seconds=poseTime(frame,config.fps,config.poseHz);
 const panel=config.panels.find(p=>frame>=p.startFrame&&frame<p.startFrame+p.frames)??config.panels[config.panels.length-1];
 const local=seconds-panel.startFrame/config.fps;
 return <AbsoluteFill style={{backgroundColor:config.background??'#fff'}}>
  <PanelScene key={panel.id} panel={panel} config={config} seconds={local}/>
  {(config.audio??[]).map((a,i)=><Sequence key={i} from={Math.round(a.at*config.fps)} durationInFrames={Math.round(a.duration*config.fps)}><Audio src={href(a.src)} volume={a.volume??1}/></Sequence>)}
 </AbsoluteFill>;
};
