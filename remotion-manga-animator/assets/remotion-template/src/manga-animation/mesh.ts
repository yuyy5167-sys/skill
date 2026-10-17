import type {ResolvedPanel,Point} from './types';
import {meshGrid,regionWeight,smooth,transformAt} from './model';
type Mesh={gl:WebGLRenderingContext;buffer:WebGLBuffer;xy:Float32Array;weights:Float32Array[];vertices:Float32Array;count:number;dispose:()=>void};
const shader=(gl:WebGLRenderingContext,type:number,source:string)=>{
 const s=gl.createShader(type)!;gl.shaderSource(s,source);gl.compileShader(s);
 if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s)??'Shader compilation failed');return s;
};
export function makeMesh(canvas:HTMLCanvasElement,panel:ResolvedPanel,img:HTMLImageElement):Mesh{
 const gl=canvas.getContext('webgl',{alpha:false,antialias:false,preserveDrawingBuffer:true});if(!gl)throw new Error('WebGL unavailable; use layers or a supported rendering browser');
 const max=gl.getParameter(gl.MAX_TEXTURE_SIZE);if(img.naturalWidth>max||img.naturalHeight>max)throw new Error(`Image exceeds GPU texture limit ${max}; prepare a smaller work image and scale all coordinates`);
 const program=gl.createProgram()!;
 const vs=shader(gl,gl.VERTEX_SHADER,'attribute vec2 a_position;attribute vec2 a_uv;varying vec2 v_uv;void main(){gl_Position=vec4(a_position,0.,1.);v_uv=a_uv;}');
 const fs=shader(gl,gl.FRAGMENT_SHADER,'precision highp float;uniform sampler2D u_image;varying vec2 v_uv;void main(){gl_FragColor=texture2D(u_image,v_uv);}');
 gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);gl.useProgram(program);
 if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program)??'Shader link failed');
 const texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);
 for(const p of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,p,gl.CLAMP_TO_EDGE);
 for(const p of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])gl.texParameteri(gl.TEXTURE_2D,p,gl.LINEAR);
 gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,img);
 const [w,h]=panel.size,{nx,ny}=meshGrid(w,h),count=(nx+1)*(ny+1);
 const xy=new Float32Array(count*2),vertices=new Float32Array(count*4),weights=panel.parts.map(()=>new Float32Array(count));
 const fixed=[...(panel.fixed??[]),...(panel.dialogues??[]).map(d=>({polygon:d.mask,feather:12}))];
 for(let y=0;y<=ny;y++)for(let x=0;x<=nx;x++){
  const i=y*(nx+1)+x,p:Point=[x*w/nx,y*h/ny];xy[i*2]=p[0];xy[i*2+1]=p[1];vertices[i*4+2]=p[0]/w;vertices[i*4+3]=p[1]/h;
  let free=smooth(Math.min(p[0],p[1],w-p[0],h-p[1])/12);for(const f of fixed)free*=1-regionWeight(p,f);
  panel.parts.forEach((part,j)=>{weights[j][i]=regionWeight(p,part)*free;});
 }
 const indices=new Uint16Array(nx*ny*6);let k=0;
 for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){const a=y*(nx+1)+x,c=a+nx+1;indices.set([a,c,a+1,a+1,c,c+1],k);k+=6;}
 const buffer=gl.createBuffer()!;gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,vertices,gl.DYNAMIC_DRAW);
 for(const [name,offset] of [['a_position',0],['a_uv',8]] as const){const loc=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,16,offset);}
 const elements=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,elements);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,indices,gl.STATIC_DRAW);gl.viewport(0,0,canvas.width,canvas.height);
 return {gl,buffer,xy,weights,vertices,count:indices.length,dispose:()=>{gl.deleteBuffer(buffer);gl.deleteBuffer(elements);gl.deleteTexture(texture);gl.deleteProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);gl.getExtension('WEBGL_lose_context')?.loseContext();}};
}
export function drawMesh(mesh:Mesh,panel:ResolvedPanel,seconds:number){
 const [w,h]=panel.size,transforms=panel.parts.map(p=>{const v=transformAt(p,seconds),r=v.angle*Math.PI/180;return {...v,c:Math.cos(r),s:Math.sin(r)};});
 for(let i=0;i<mesh.xy.length/2;i++){
  const x=mesh.xy[i*2],y=mesh.xy[i*2+1];let dx=0,dy=0;
  panel.parts.forEach((p,j)=>{const a=mesh.weights[j][i];if(!a)return;const t=transforms[j],px=x-p.pivot[0],py=y-p.pivot[1];dx+=a*(px*(t.c-1)-py*t.s+t.dx);dy+=a*(px*t.s+py*(t.c-1)+t.dy);});
  mesh.vertices[i*4]=(x+dx)/w*2-1;mesh.vertices[i*4+1]=1-(y+dy)/h*2;
 }
 const gl=mesh.gl;gl.bindBuffer(gl.ARRAY_BUFFER,mesh.buffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,mesh.vertices);gl.clearColor(1,1,1,1);gl.clear(gl.COLOR_BUFFER_BIT);gl.drawElements(gl.TRIANGLES,mesh.count,gl.UNSIGNED_SHORT,0);gl.finish();
}
