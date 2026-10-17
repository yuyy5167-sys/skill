import fs from 'node:fs/promises';
import path from 'node:path';
import {renderMedia} from '@remotion/renderer';
import {loadConfig,openRender} from './common.mjs';
const args=process.argv.slice(2),get=flag=>{const i=args.indexOf(flag);if(i<0)return undefined;if(!args[i+1]||args[i+1].startsWith('--'))throw new Error(`${flag} needs a value`);return args[i+1];};
const c=await loadConfig(),range=get('--frames'),output=path.resolve(get('--output')??`output/${c.id}.mp4`);
let frameRange;
if(range){const m=/^(\d+)-(\d+)$/.exec(range);if(!m)throw new Error('--frames uses inclusive start-end');frameRange=[Number(m[1]),Number(m[2])];if(frameRange[0]>frameRange[1]||frameRange[1]>=c.frames)throw new Error('Frame range exceeds the composition');}
await fs.mkdir(path.dirname(output),{recursive:true});
const {serveUrl,browser,composition}=await openRender(c);
try{
 let last=-1;
 await renderMedia({serveUrl,composition,puppeteerInstance:browser,codec:'h264',crf:16,pixelFormat:'yuv420p',outputLocation:output,frameRange,concurrency:Math.max(1,Number(process.env.MANGA_CONCURRENCY)||2),onProgress:p=>{const stage=Math.floor(p.progress*10);if(stage!==last){last=stage;console.log(`${stage*10}%`);}}});
 console.log(`Saved ${output}`);
}finally{await browser.close({silent:true});}
