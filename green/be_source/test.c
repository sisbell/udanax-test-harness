/* Copyright � 1979-1999 Udanax.com. All rights reserved.

* This code is licensed under the terms of The Udanax Open-Source License,
* which contains precisely the terms of the X11 License.  The full text of
* The Udanax Open-Source License can be found in the distribution in the file
* license.html.  If this file is absent, a copy can be found at
* http://udanax.xanadu.com/license.html and http://www.udanax.com/license.html
*/
/*
 *      testenf.c -- a file of functions written to test
 *      Two dimensional enfilades
 *      created 79/11/12
 *      modified as intest.c to test
 *      2d, Span and Gran enfilades
 *      on 80/10/12
 */

#include "xanadu.h"
#include "enf.h"
#include "ndenf.h"
#include "coredisk.h"

extern bool gettumbler();

extern typecorecrum *grimreaper;
extern INT reservnumber;
INT numfoo = NUMDISKBLOCKSINLOAF;
                          
extern char end;        /* lower limit (pointers should be into alloc space */
extern char etext;   /* as another lower limit on valid pointers */

long nolread;
long nowread;

int foo(char *msg)
{
#ifndef DISTRIBUTION
        if (debug)
                fprintf (stderr, msg);
#endif
}

int foospan(char *msg, typespan *span)
{
#ifndef DISTRIBUTION
        if(debug){
                fprintf(stderr,msg);
                dumpspan(span);
        }
#endif
}                    

int foospanset(char *msg, typespan *spanset)
{
#ifndef DISTRIBUTION
        if(debug){
                fprintf(stderr,msg); 
                if(!spanset){
                        fprintf(stderr,"null spanset\n");
                }else{
                        for(;spanset;spanset = spanset->next){
                                dumpspan(spanset);
                        }
                }
        }
#endif
}

int dumpspanset(typespan *spanset)
{
#ifndef DISTRIBUTION
                if(!spanset){
                        fprintf(stderr,"null spanset\n");
                }else{
                        for(;spanset;spanset = spanset->next){
                                dumpspan(spanset);
                        }
                }
#endif
}

int foocrum(char *msg, typecorecrum *crumptr)
{
#ifndef DISTRIBUTION
        if(debug){
                fprintf(stderr,msg);
                dump(crumptr);  
        }
#endif
}

int foohex(char *msg, INT num)
{
#ifndef DISTRIBUTION
        if (debug)
                fprintf (stderr, "%s %x\n", msg, num);
#endif
}

int foodec(char *msg, INT num)
{
#ifndef DISTRIBUTION
        if (debug)
                fprintf (stderr, "%s %d\n", msg, num);
#endif
}

int foocontext(char *msg, typecontext *context)
{
#ifndef DISTRIBUTION
        if (debug) {
                fprintf (stderr, msg);
                dumpcontext (context);
        }
#endif
}

int foocontextlist(char *msg, typecontext *context)
{
#ifndef DISTRIBUTION
        if (debug) {
                fprintf (stderr, msg);
                dumpcontextlist (context);
        }
#endif
}

int fooitemset(char *msg, typeitemset iptr)
{
#ifndef DISTRIBUTION
        if (debug) {
                fprintf (stderr, msg);
                dumpitemset (iptr);
        }
#endif
}

int fooitem(char *msg, typeitem *iptr)
{
#ifndef DISTRIBUTION
        if (debug) {
                fprintf (stderr, msg);
                dumpitem (iptr);
                fprintf (stderr, "\n");
        }
#endif
}

int footumbler(char *msg, tumbler *tptr)
{
#ifndef DISTRIBUTION
        if (debug) {
                fprintf (stderr, msg);
                if (tptr)
                        puttumbler (stderr, tptr);
                else
                        fprintf (stderr, "NULL");
                fprintf (stderr, "\n");
        }
#endif
}

int foodsp(char *msg, typedsp *dptr, INT enftype)
{
#ifndef DISTRIBUTION
        if (debug) {
                fprintf (stderr, msg);
                if (dptr)
                        dumpdsp (dptr, enftype);
                else
                        fprintf (stderr, "NULL");
                fprintf (stderr, "\n");
        }
#endif
}

int foowid(char *msg, typewid *wptr, INT enftype)
{
#ifndef DISTRIBUTION
        if (debug) {
                fprintf (stderr, msg);
                if (wptr)
                        dumpwid (wptr, enftype);
                else
                        fprintf (stderr, "NULL");
                fprintf (stderr, "\n");
        }
#endif
}
/* pass this the fullcrum to dump the entire (incore) enfilade */
int dumpsubtree(typecuc *father)
{ 
#ifndef DISTRIBUTION
  typecorecrum *ptr;

        if (father->cenftype == POOM) {
                dumppoomwisps (father);
                return;
        }
        dump (father);
        if (father->height <= 0)
                return;
        for (ptr = father->leftson; ptr; ptr = ptr->rightbro)
                dumpsubtree (ptr);
#endif
}
int dumpwholesubtree(typecuc *father)
{ 
#ifndef DISTRIBUTION
  typecorecrum *ptr;
fprintf(stderr,"dump whole subtree");

        if (father->cenftype == POOM) {
                dumppoomwisps (father);
                return;
        }
        dump (father);
        if (father->height <= 0)
                return;
        for (ptr = findleftson(father); ptr; ptr = findrightbro(ptr))
                dumpwholesubtree (ptr);
#endif
}

int assertspecisstring(typespecset specptr, char *string)
{
#ifndef DISTRIBUTION
  typetask taskfoo;
  typevstuffset vstuffset;
  INT i;
  INT savedebug ;
fprintf(stderr,"assertspecisstring entering \n");
savedebug = debug;
/*debug = FALSE;*/
inittask(&taskfoo);
	doretrievev(&taskfoo,specptr,&vstuffset);
/*	for(i=0;(i<vstuffset->length)&&(string[i] == vstuffset->string[i]);i++)
		;
	if(i != vstuffset->length){
		fprintf(stderr,"in assertspecisstring failedstring1 =%s string2 =%s %d\n",string,vstuffset->string,vstuffset->length);
debug = TRUE;
fooitem("spec is ",specptr);
fooitem("\nvstuff is ",vstuffset);
		// crash bang boom //
		gerror("assertspecisstring asserton failed \n");
	}
fprintf(stderr,"in assertspecisstring succeded %s \n",string);
*/
		fprintf(stderr,"in assertspecisstring string2 =%s %d\n",vstuffset->xxxtext.string,vstuffset->xxxtext.length);
	tfree(&taskfoo);
debug = savedebug;
fprintf(stderr,"assertspecisstring leaving \n");
#endif
}

bool asserttreeisok(typecorecrum *ptr)
{
return(TRUE);
/*fprintf(stderr,"entering asserttreeisok\n");*/
/*        for(;!isfullcrum(ptr);ptr=(typecorecrum *)findfather(ptr))
                ;
        assertsubtreeisok(ptr);
return(TRUE);
*/
}

int assertsubtreeisok(typecorecrum *ptr)
{
#ifndef DISTRIBUTION 
  typecorecrum *son;

        if(!ptr){
                gerror("assertsubtreeok failed null ptr\n");
	}
	assertwidsarepositive(ptr);
	if(!reservnumber){
		if(ptr->age == RESERVED){
			dump(ptr);
			gerror("incorrect reserved in assertsubtreeisok");
		}
	}
        if(ptr->height == 0){
                return;
        }
/*        if(toomanysons(ptr)){
        //      dump(ptr);
                fprintf(stderr,"fatherhas too many sons\n");//
                //gerror("foo");//
        }
*/
        assertsonswispmatchesfather(ptr);
        for(son =((typecuc *)ptr)->leftson/* findleftson//getleftson//(ptr)*/;son;son = son->rightbro){
                assertsubtreeisok(son);
        }
#endif
}

int assertsonswispmatchesfather(typecuc *father)
{
#ifndef DISTRIBUTION
  typecorecrum *son;
        if(father->numberofsons == 0){
                if(father->sonorigin.diskblocknumber != DISKPTRNULL){
                        return;
                }
                fprintf(stderr,"zerosons in assert\n");
                return;
        }
        if(setwisp(father)){ 
                fprintf(stderr,"assert wisp matched father failed \n");
                dump(father);
                dumpwholetree(father);
                /*fprintf(stderr,*/gerror(/**/"father didn't match sons wid and disp\n");
        }
#endif
}
int assertwidsarepositive(typecorecrum *ptr)
{
#ifndef DISTRIBUTION
  INT nstreams,i;
  INT enftype;
	enftype = ptr->cenftype;

        if (enftype == GRAN)
                return;
        nstreams = widsize (enftype);
        for (i = 0; i < nstreams; ++i) {
                tumblercheckptr(&(ptr->cwid.dsas[i]),(INT*)ptr);
        }
        nstreams = dspsize (enftype);
        for (i = 0; i < nstreams; ++i) {
                tumblercheckptr(&(ptr->cdsp.dsas[i]),(INT*)ptr);
        }
#endif
}

int dumpwholetree(typecorecrum *ptr)
{
#ifndef DISTRIBUTION
fprintf(stderr,"dump whole tree\n");
        for(;!isfullcrum(ptr);ptr =(typecorecrum *) findfather(ptr))
                ;
        dumpwholesubtree(ptr);
#endif
}
  
int checkwholesubtree(typecuc *father)
{ 
#ifndef DISTRIBUTION
  typecorecrum *ptr;
return(0);
#ifdef UndEfIneD
        if(!father)
                return(0);                 
        if(check (father)){
                fprintf(stderr,"found something bad in checkwholesubtree\n");
                dumpsubtree(father);
                /*gerror("in checkwholesubtree");*/
                
                 return(1);
        }
        if (father->height <= 0)
                return(0);
        for (ptr =father->leftson; ptr; ptr = ptr->rightbro)
                if(checkwholesubtree (ptr))
                          return(1); 
        return(0);
#endif
#endif
}

int check(typecuc *ptr)
{
return(0);
#ifdef UnDeeFiNeD
       if(ptr->height == 0){
                return(0);
        }
	if(ptr->leftson==NULL/*&&ptr->sonorigin.diskblocknumber==-1*/&&ptr->modified){
	    dump(ptr);
	    gerror("in check\n");
        }else{
	    return(0);
        }
        gerror("check: can't get ther\n");
return(0);
#endif
}
               /* dump a core crum */
int dump(typecorecrum *ptr)
{
#ifndef DISTRIBUTION
    fprintf(stderr,"\n");
    dumphedr(ptr);
    if(ptr->height) {
	fprintf(stderr,"sonorigin = %x insideloaf %x  leftson = %x  #sons = %x\n",
		((typecuc *)ptr)->sonorigin.diskblocknumber, 
		((typecuc *)ptr)->sonorigin.insidediskblocknumber, 
		((typecuc *)ptr)->leftson, ((typecuc *)ptr)->numberofsons);
    } else{
	dumpinfo (&((typecbc *)ptr)->cinfo, ptr->cenftype);
    }
#endif
}

int yesdump(typecorecrum *ptr)   /* because dbx has a builtin dump   name conflict*/
{
#ifndef DISTRIBUTION
        dump(ptr);
#endif
}
                 /* dump a corecrumhedr */
int dumphedr(typecorecrumhedr *ptr)
{
#ifndef DISTRIBUTION
  char *temp;
  char *full;

        switch (ptr->cenftype) {
         case GRAN:     temp = "GRAN";
                        break;
         case SPAN:     temp = "SPAN";
                        break;
         case POOM:     temp = "POOM";
                        break;
         default:       temp = "bad enftype";
                        fprintf(stderr, " %d ",ptr->cenftype);
        }
        full = (ptr->isapex ? "full" : "");
        fprintf(stderr,"%s %scrum core location = %x\n", temp, full, ptr);
       fprintf(stderr,"height = %x nextcrum = %x  modified = %x\n",
            ptr->height, ptr->nextcrum, ptr->modified);
        fprintf(stderr," age = %x ",ptr -> age);
        fprintf(stderr,"isleftmost = %x leftbro = %x rightbro = %x\n",
            ptr->isleftmost,ptr->leftbroorfather,ptr->rightbro);
        dumpdsp (&ptr->cdsp, ptr->cenftype);
        dumpwid (&ptr->cwid, ptr->cenftype);
#endif
}

int dumpwid(typewid *widptr, INT enftype)
{
#ifndef DISTRIBUTION
  INT i, nstreams;

        nstreams = widsize (enftype);
        fprintf(stderr,"wid = < ");
        for (i = 0; i < nstreams; ++i) {
                if (i > 0)
                        fprintf(stderr," , ");
                puttumbler (stderr, &widptr->dsas[i]);
        }
        fprintf(stderr," >\n");
#endif
}

int dumpdsp(typewid *dspptr, INT enftype)
{
#ifndef DISTRIBUTION
  INT i, nstreams;

        /*if (enftype == GRAN)
                return; */
        nstreams = dspsize (enftype);
        fprintf(stderr,"dsp = < ");
        for (i = 0; i < nstreams; ++i) {
                if (i > 0)
                        fprintf(stderr," , ");
                puttumbler (stderr, &dspptr->dsas[i]);
        }
        fprintf(stderr," >\n");
#endif
}

int dumpinfo(typegranbottomcruminfo *infoptr, INT enftype)
{
#ifndef DISTRIBUTION
        if (enftype == GRAN) {
                switch (infoptr->infotype) {
                  case GRANTEXT:
                        fprintf(stderr,"text:  %s\n", infoptr->granstuff.textstuff.textstring);
                        break;
                  case GRANORGL:
                        fprintf(stderr," diskorgl %x, ",infoptr->granstuff.orglstuff.diskorglptr);
                        fprintf(stderr,"orgl %x\n ", infoptr->granstuff.orglstuff.orglptr);
                        break;
		  case GRANNULL:
			fprintf(stderr,"GRANNULL info\n");
			break;
                  default :
                        fprintf(stderr,"empty infotype: %d\n", infoptr->infotype);
			gerror("bad in dumpinfo \n");
                }
        } else {
                fprintf(stderr,"home document: ");
                puttumbler (stderr, &((type2dbottomcruminfo *)infoptr)->homedoc);
                fprintf(stderr,"\n");
        }
#endif
}

int dumptumbler(tumbler *tumblerptr)
{
#ifndef DISTRIBUTION
  INT i;
        if(!tumblerptr){
                fprintf(stderr,"NULL POINTER TO TUMBLER");
                return;
        }

	if (!debug)
		puttumbler(stderr,tumblerptr);
	else {
	        fprintf(stderr," %d | ",tumblerptr->sign);
	        fprintf(stderr,"%d | ",tumblerptr->exp);
	        for(i = 0; i < NPLACES; ++i)
        	        fprintf(stderr,"%d ", tumblerptr->mantissa[i]);
		if(tumblerptr->exp >0){
			fprintf(stderr,"in dumptumbler exponent positive i.e. negative number of leading zeros!\n");
			gerror("dumptumbler");
		}
	}
#endif
}

int displaycutspm(typeknives *knivesptr)
{
#ifndef DISTRIBUTION
  INT i;

        fprintf(stderr,"%x cuts:", knivesptr->nblades);
        for(i = 0; i < knivesptr->nblades; ++i) {
                fprintf(stderr,"\n       ");
                puttumbler (stderr, &knivesptr->blades[i]);
        }
        fprintf(stderr,"\n");
#endif
}


int dumphint(typehint *hintptr)
{
#ifndef DISTRIBUTION
        fprintf(stderr,"\nHINT\n");
        fprintf(stderr,"  supertype: %d\n", hintptr->supertype);
        fprintf(stderr,"  subtype:   %d\n", hintptr->subtype);
        fprintf(stderr,"  atomtype:  %d\n", hintptr->atomtype);
        fprintf(stderr,"  isa:       ");
        puttumbler (stderr, &hintptr->hintisa);
        fprintf(stderr,"\n");
#endif
}

int examine(typetask *taskptr)
{
#ifndef DISTRIBUTION
  char c;
  typeisa orglisa;
  typeorgl orgl;

        prompt (taskptr, "\nspanf (s), orgl (o) or istream (i) ? ");
        c = getc(taskptr->inp);
        if (c != '\n')
                getc (taskptr->inp);
        fprintf (stderr, "\n");
        switch (c) {
          case 'i':
                showistream (granf);
                break;
          case 's':
                showspanf (spanf);
                break;

          case 'o':
          /*      prompt (taskptr, "orgl isa => ");
                if (!(
                    gettumbler (taskptr, &orglisa)
                 && findorgl (taskptr, granf, &orglisa, &orgl,READBERT))) {
                        fprintf(stderr,taskptr->errp, "\nnot found\n");
                } else {
                        showspanf (orgl);
                }*/
                showorgl(taskptr);
                break;

          default:
                return;
        }
#endif
}


int showorgl(typetask *taskptr)
{
#ifndef DISTRIBUTION
  typeorgl orgl;
  typeisa orglisa;
  bool findorgl();

        prompt (taskptr, "orgl isa => ");
        if (!(
           gettumbler (taskptr, &orglisa)
        && findorgl (taskptr, granf, &orglisa, &orgl,READBERT))) {
                fprintf(stderr, "\nnot found\n");
        } else {
                showsubtree (orgl);
        }
#endif
}

int showsubtree(typecorecrum *father)
{
#ifndef DISTRIBUTION
  INT temp;
/*        temp = debug;
        debug = 5; */
       dumpwholesubtree (father);
/*        debug = temp;*/
#endif
}

int showistream(typecuc *granfptr)
{
#ifndef DISTRIBUTION
  INT temp;
/*        temp = debug;
        debug = 5; */
        dumpistreamgr (granfptr);
/*        debug = temp;*/
#endif
}

int showspanf(typecuc *spanfptr)
{
#ifndef DISTRIBUTION
  typedsp offset;
  INT enfheight;

        clear (&offset, sizeof(typedsp));
        enfheight = spanfptr->height;
        fprintf(stderr,"\n");
        doshowspanf (spanfptr, &offset, enfheight);
#endif
}


int doshowspanf(typecorecrum *crumptr, typedsp *offsetptr, INT enfheight)
{ 
#ifndef DISTRIBUTION
  typecorecrum *ptr;
  typedsp loffset;
        showspanfcrum (crumptr, offsetptr, enfheight);
        if (crumptr->height <= 0)
                return;
        dspadd (offsetptr, &crumptr->cdsp, &loffset,crumptr ->cenftype);
        for (ptr = findleftson (crumptr); ptr; ptr = ptr->rightbro)
                doshowspanf (ptr, &loffset, enfheight);
#endif
}

int showspanfcrum(typecorecrum *crumptr, typedsp *offsetptr, INT enfheight)
{
#ifndef DISTRIBUTION
  INT depth;
  typedsp lstream;

        for (depth = enfheight - crumptr->height; depth--;)
                fprintf(stderr,"  ");
        fprintf(stderr,"[spandsp");
        dspadd (offsetptr, &crumptr->cdsp, &lstream,crumptr->cenftype);
        puttumbler (stderr, &lstream.dsas[SPANRANGE]);
        fprintf(stderr," ,spanwid  ");
        puttumbler (stderr, &crumptr->cwid.dsas[SPANRANGE]);
        fprintf(stderr,"]\n");
        for (depth = enfheight - crumptr->height; depth--;)
                fprintf(stderr,"  ");
        fprintf(stderr,"[orgldsp ");
        puttumbler (stderr, &lstream.dsas[ORGLRANGE]);
        fprintf(stderr," ,orglwid  ");
        puttumbler (stderr, &crumptr->cwid.dsas[ORGLRANGE]);
        fprintf(stderr,"]   ");
        if (crumptr->height == 0)
                puttumbler (stderr, &((type2dcbc *)crumptr)->c2dinfo.homedoc);
        fprintf(stderr,"\n\n");
#endif
}

int dumpmem(char *loc, unsigned count)
{
#ifndef DISTRIBUTION
       INT i;

        fprintf(stderr," loc = %x\n", loc);
        for (i = 0; count--; ++loc, (i+1 < 64 ? ++i : (i = 0))) {
                if ((*loc & 0x7f) < ' ')
                        fprintf(stderr,"%c",'.');
                else
                        fprintf(stderr,"%c",*loc);
        if (i == 63)
                  fprintf(stderr,"\n");
        }
          fprintf(stderr,"\n");
#endif
}

bool dumpgranfwids(typetask *taskptr)
{
#ifndef DISTRIBUTION
  tumbler subtreewid;
  INT fullheight;

        /*fullheight = ((typecorecrum *)granf)->height;*/
        showgranwids (granf, 0, &subtreewid);
        if (!tumblereq (&subtreewid, &((typecorecrum *)granf)->cwid.dsas[WIDTH])) {
                fprintf (stderr, "Granfilade fullcrum wid and widded enfilade don\'t match.\n");
                fprintf (stderr, "gran fullcrum wid ");
                puttumbler (stderr, &((typecorecrum *)granf)->cwid.dsas[WIDTH]);
                fprintf (stderr, "\nreturned wid from subtree ");
                puttumbler (stderr, &subtreewid);
                fprintf (stderr, "\nHit \"<return>\" to continue, \"a<return>\" to abort ");
                if (getc (taskptr->inp) == 'a')
                        abort ();
        }
        fprintf (stderr,"\n");
#endif
        return (TRUE);
}

int showgranwids(typecorecrum *crum, INT down, tumbler *retptr)        /* down is distance from top */
{
#ifndef DISTRIBUTION
  typecorecrum *ptr;
  tumbler subtreewid;
  INT i;

        fprintf (stderr,"\n");
        clear (retptr, sizeof (*retptr));
        for (i = 0; i < down; ++i)
                fprintf (stderr,"        ");
        fprintf (stderr,"%x (%d%c) < ", crum, crum->height,(crum->modified?'M':'-'));
        puttumbler (stderr, &crum->cwid.dsas[WIDTH]);
        fprintf (stderr," >");
        if (crum->height != 0) {
                if (((typecuc *)crum)->leftson) {
                        for (ptr = ((typecuc *)crum)->leftson; ptr; ptr = ptr->rightbro) {
                                tumbleradd (retptr, &ptr->cwid.dsas[WIDTH], retptr);
                                showgranwids (ptr, down+1, &subtreewid);
                                if (!tumblereq (&subtreewid, &ptr->cwid.dsas[WIDTH])) {
                                        fprintf (stderr, "\n%d level crum\'s wid and result from subtree don\'t match\n", crum->height);
                                        fprintf (stderr, "father wid ");
                                        puttumbler(stderr,&ptr->cwid.dsas[WIDTH]);
                                        fprintf (stderr, "\nreturned wid ");
                                        puttumbler (stderr, &subtreewid);
                                        fprintf (stderr, "\n");
                                }
                        }
                } else {
                        fprintf (stderr," disksonloaf = %x ", ((typecuc *)crum)->sonorigin.diskblocknumber);
                        movetumbler (&crum->cwid.dsas[WIDTH], retptr);
                        /* so that lacking incore sons will not cause error */
                }
        } else if (((typecbc *)crum)->cinfo.infotype == GRANORGL) {
                if (((typecbc *)crum)->cinfo.granstuff.orglstuff.orglincore)
                        fprintf (stderr," orgl %x ", ((typecbc *)crum)->cinfo.granstuff.orglstuff.orglptr);
                else
                        fprintf (stderr," diskorgl %x", ((typecbc *)crum)->cinfo.granstuff.orglstuff.diskorglptr);
                movetumbler (&crum->cwid.dsas[WIDTH], retptr);
        } else
                movetumbler (&crum->cwid.dsas[WIDTH], retptr);
#endif
}

int dumppoomwisps(typecorecrum *orgl)
{
#ifndef DISTRIBUTION
  INT fullheight;

        /*fullheight = orgl->height;*/
        showpoomwisps (orgl, 0);
        fprintf (stderr,"\n");
#endif
}

int showpoomwisps(typecuc *crum, INT down)        /* down is distance from top */
{
#ifndef DISTRIBUTION
  typecorecrum *ptr;
  INT i;

        fprintf (stderr,"\n");
        for (i = 0; i < down; ++i)
                fprintf (stderr,"   ");
        fprintf (stderr,"%x (%d%c) <Idsp ", crum, crum->height,(crum->modified?'M':'-'));
        puttumbler (stderr, &crum->cdsp.dsas[I]);
        fprintf (stderr,",Vdsp ");
        puttumbler (stderr, &crum->cdsp.dsas[V]);
        fprintf (stderr," > <Iwid ");
        puttumbler (stderr, &crum->cwid.dsas[I]);
        fprintf (stderr,",Vwid ");
        puttumbler (stderr, &crum->cwid.dsas[V]);
        fprintf (stderr," >");
        if (crum->height != 0) {
                if (crum->leftson) {
                        for (ptr =findleftson(crum);ptr; ptr = ptr->rightbro) {
                                showpoomwisps (ptr, down+1);
                        }
                } else {
                        fprintf (stderr," disksonloaf = %x ", crum->sonorigin.diskblocknumber);
                }
        }
#endif
}

#define TABSTOP 20

int dumpistreamgr(typecuc *crumptr)
{
#ifndef DISTRIBUTION
 tumbler offset;
if (debug < 5) return;
        tumblerclear (&offset);
        dodumpistreamgr (crumptr, &offset);
#endif
}

int dodumpistreamgr(typecuc *crumptr, tumbler *offsetptr)
{
#ifndef DISTRIBUTION
  typecorecrum *ptr;
        if (crumptr->height == 0) {
                dumpmoleculegr (offsetptr, crumptr);
                tumbleradd (offsetptr, &crumptr->cwid.dsas[WIDTH], offsetptr);
                return;
        }
        for (ptr = findleftson (crumptr); ptr; ptr = ptr->rightbro)
                dodumpistreamgr (ptr, offsetptr);
#endif
}

int dumpmoleculegr(tumbler *offsetptr, typecbc *cbcptr)
{
#ifndef DISTRIBUTION
 INT i;
  tumbler localoffset;
/*        fprintf(stderr,"\n");
        dumpisagr (offsetptr);
        if (cbcptr->cinfo.infotype == GRANTEXT) {
                if (cbcptr->cinfo.textstring[0] == '\n')
                        fprintf(stderr,"\\n");
                  else if (cbcptr->cinfo.textstring[0] == '\t')
                        fprintf(stderr,"\\t");
                  else
                        fprintf(stderr,"%c ",cbcptr->cinfo.textstring[0]);
                fprintf(stderr,"    | %x  ", cbcptr);
                dumpwid (&cbcptr->cwid, GRAN);
                movetumbler (offsetptr, &localoffset);
                for (i = 1; i < cbcptr->cinfo.textlength; ++i){
                        tumblerincrement (&localoffset, 0, 1, &localoffset);
                        dumpisagr (&localoffset);
                        if (cbcptr->cinfo.textstring[i] == '\n')
                                fprintf(stderr,"\\n");
                          else if (cbcptr->cinfo.textstring[i] == '\t')
                                fprintf(stderr,"\\t");
                          else
                                fprintf(stderr,"%c ",cbcptr->cinfo.textstring[i]);
                        fprintf(stderr,"    |\n");
                }
        } else if (cbcptr->cinfo.infotype == GRANORGL) {
                fprintf(stderr,"%x",cbcptr->cinfo.orglptr);
                fprintf(stderr,"  | %x  ", cbcptr);
                dumpwid (&cbcptr->cwid, GRAN);
        } else {
                fprintf(stderr,"      | %x  ", cbcptr);
                dumpwid (&cbcptr->cwid, GRAN);
        }
*/
#endif
}

int dumpisagr(tumbler *offsetptr)
{
#ifndef DISTRIBUTION
 INT i, j, k;
  tumbler offset;
        movetumbler (offsetptr, &offset);
        i = nstories (&offset) - offset.exp;
        i += i - 1;
        for (j = 0; j < NPLACES; ++j)
                for (k = offset.mantissa[j]; k /= 10; ++i);
        i = TABSTOP - i;
        if (i < 2) {
                fprintf(stderr,"too long");
                i = 8;
        } else
                puttumbler (stderr, &offset);
        while (i--)
                fprintf(stderr," ");
#endif
}

typecorecrum *checkenftypes(typecuc *father, char *message)
{ 
#ifndef DISTRIBUTION
  typecorecrum *ptr;
if(grimreaper == NULL)
 fprintf(stderr,"grimreaper tests null");
return((typecorecrum *)father);
/*        if (!father) {
                fputs(stderr,message);
                qerror ("ARGH!! null father ptr");
        }
        if (!father->height)
                return (father);
        if (father->cenftype == SPAN) {
                if (father->cwid.dsas[ORGLRANGE].exp == 0 && father->cwid.dsas[ORGLRANGE].mantissa[0] > 2) {
                        dumpsubtree(father);
                        fputs(stderr,message);
                        qerror ("I think the wid is too big.");
                }
        }
        for (ptr = father->leftson; ptr; ptr = ptr->rightbro){
                if (ptr->cenftype != GRAN && ptr->cenftype != POOM && ptr->cenftype != SPAN) {
                        fputs(stderr,message);
                        qerror ("bad enftype");
                }
                if (ptr->cenftype != father->cenftype) {
                        fputs(stderr,message);
                        qerror ("enftype mismatch");
                }
                checkenftypes (ptr, message);
        }
        return (father);
*/
#endif
}

typecorecrum *checkthebleedingcrum(typecorecrum *crumptr)
{
#ifndef DISTRIBUTION
if(grimreaper == NULL)
 fprintf(stderr,"grimreaper tests null");
return(crumptr);
/*        if(!crumptr){
                qerror("checkbleeding NULL crum");
        }
        if (crumptr->cenftype != GRAN && crumptr->cenftype != SPAN && crumptr->cenftype != POOM){
                fprintf(stderr,"Bad enftype in check the bleeding crum\n\n\n");
                dump(crumptr);
                qerror ("Bad enftype\n");
        }
        if (!crumptr->isapex&&crumptr->leftbroorfather..disowned.. && crumptr->cenftype != crumptr->leftbroorfather->cenftype){
                dump(crumptr);
                fprintf(stderr,"\n\n\n  and here comes the spanf \n");
                dumpsubtree(spanf);
                dump(crumptr);
                qerror ("Enftype mismatch.\n");
        }
        if(crumptr->cenftype !=GRAN){
                if(!tumblercheck(&crumptr->cdsp.dsas[V])){
                        qerror("cleckbleeding disp V");
                }
                if(!tumblercheck(&crumptr->cdsp.dsas[I])){
                        qerror("cleckbleeding disp I");
                }
        }
        return (crumptr);
*/
#endif
}

int teststack(void)
{
  INT testloc;

/*      checkalloc ("");*/
}

char *enftypestring(INT type)
{
#ifndef DISTRIBUTION
  static char errbuf[60];
/*  char * sprintf(); /* already defined in stdio.h 1998/04/29 ADP */

        switch (type) {
          case GRAN:
                return ("GRAN");
          case POOM:
                return ("POOM");
          case SPAN:
                return ("SPAN");
          default:
                sprintf (errbuf, "bad enftype %d", type);
                return ((char *)errbuf);
        }
#endif
}

typecorecrum *sonoriginok(typecorecrum *father)
{
  bool goodblock();
return (father);/*
        if (!father)
                return (father);
        if (father->height == 0)
                return (father);
        if (father->sonorigin.diskblocknumber == -1)
                return (father);
        if (goodblock (father->sonorigin.diskblocknumber))
                return (father);
        dumpsubtree (father);
fprintf(stderr,"enter y to procede\n");
if(getchar() == 'y') {
getchar();
        return(father);
}
        gerror ("Bad Sonorigin.\n");
	return(NULL);// for lint//
*/
}

int dumpcontextlist(typecontext *context)
{
#ifndef DISTRIBUTION
        fprintf (stderr, "contextlist :\n");
        if (!context) {
                fprintf (stderr, "  contextlist NULL\n");
                return;
        }
        for (;context; context = context->nextcontext) {
                dumpcontext (context);
        }
#endif
}

int dumpcontext(typecontext *context)
{
#ifndef DISTRIBUTION
  char *enftypestring();

        fprintf (stderr, "  context %x:\n", context);
    if(context == NULL){
                fprintf(stderr,"NULL context\n");
                return;
        }
        fprintf (stderr, "    contexttype %s\n", enftypestring (context->contexttype));
        fprintf (stderr, "    totaloffset ");
        dumpdsp (&context->totaloffset, context->contexttype);
        fprintf (stderr, "    contextwid ");
        dumpwid (&context->contextwid, context->contexttype);
        if (debug > 1) {
                fprintf (stderr, "    contextinfo ");
                dumpinfo (&context->contextinfo, context->contexttype);
        }
#endif
}

int dumpitemset(typeitemset itemset)
{
#ifndef DISTRIBUTION
        if (itemset == NULL)
                fprintf (stderr, "  \nitemset empty\n");
        for (; itemset; itemset = (typeitemset)((typeitemheader *)itemset)->next) {
                dumpitem (itemset);
                if (!(((typeitemheader *)itemset)->next && ((typeitemheader *)itemset)->itemid == TEXTID && ((typeitemheader *)itemset)->next->itemid == TEXTID))
                        putc ('\n', stderr);
        }
#endif
}

int dumpitem(typeitem *itemptr)
{
#ifndef DISTRIBUTION
  INT bugger = debug;

        debug = 0;
        /*checkitem ("dumpitem: ", itemptr);*/
        fprintf (stderr, "%x ->%x:", itemptr, ((typeitemheader *)itemptr)->next);
        switch (((typeitemheader *)itemptr)->itemid) {
          case ISPANID:
                fprintf (stderr, "  ispan\n");
                dumpspan (itemptr);
                break;
          case VSPANID:
                fprintf (stderr, "  vspan\n");
                dumpspan (itemptr);
                break;
          case VSPECID:
                fprintf (stderr, "document: ");
                puttumbler (stderr, &((typevspec *)itemptr)->docisa);
                fprintf (stderr, "\nspans");
                dumpitemset (((typevspec *)itemptr)->vspanset);
                break;
          case TEXTID:
                dumptext (itemptr);
                break;
          case LINKID:
                puttumbler (stderr, &((typelink *)itemptr)->address);
                break;
          case SPORGLID:
                fprintf (stderr, "sporgl address: ");
                puttumbler (stderr, &((typesporgl *)itemptr)->sporgladdress);
                fprintf (stderr, "\n   sporgl origin: ");
                puttumbler (stderr, &((typesporgl *)itemptr)->sporglorigin);
                fprintf (stderr, "\n   sporgl width: ");
                puttumbler (stderr, &((typesporgl *)itemptr)->sporglwidth);
                fprintf (stderr, "\n");
                break;

          default:
                fprintf (stderr, "illegal item id for dumpitem ");
                fprintf (stderr, "%x  %d\nd",itemptr,((typeitemheader *)itemptr)->itemid);
		gerror("Illegal item in dumpitem!\n");
        }
        debug = bugger;
#endif
}

int dumpspan(typespan *spanptr)
{
#ifndef DISTRIBUTION
if(!spanptr){
fprintf(stderr,"null span ptr\n");
return;
}

        fprintf(stderr, "   span address: ");
        puttumbler(stderr, &spanptr->stream);
        fprintf(stderr, "   span width: ");
        puttumbler(stderr, &spanptr->width);
	fprintf(stderr,"\n");
#endif
}

int dumptext(typetext *textptr)
{
#ifndef DISTRIBUTION
        write (2, textptr->string, textptr->length);
#endif
}

bool ioinfo(typetask *taskptr)
{
#ifndef DISTRIBUTION
        fprintf (stderr,"Total reads = %ld,  total writes = %ld\n", nolread, nowread);
#endif
        return (TRUE);
}


bool showenfilades(typetask *taskptr)
{
#ifndef DISTRIBUTION
  char c;

        prompt (taskptr, "\ngranf (g), spanf (s) or orgl (o) ? ");
        c = getc(taskptr->inp);
        if (c != '\n')
                getc (taskptr->inp);
        fprintf (stderr/*taskptr->outps*/, "\n");
        switch (c) {
          case 'o':
                showorgl (taskptr);
                break;
          case 'g':
                showsubtree (granf);
                break;
          case 's':
                showsubtree (spanf);
                break;
          default:
                break;
        }
#endif
}

char *itemidstring(typeitem *item)
{
#ifndef DISTRIBUTION
        switch (((typeitemheader *)item)->itemid) {
          case TEXTID:
                return ("TEXTID");
          case ISPANID:
                return ("ISPANID");
          case VSPANID:
                return ("VSPANID");
          case VSPECID:
                return ("VSPECID");
          case NODEID:
                return ("NODEID");
          case ADDRESSID:
                return ("ADDRESSID");
          case SPORGLID:
                return ("SPORGLID");
        }
#endif
return(NULL); /* for lint ?*/
}

int checkitem(char *msg, typeitem *ptr)
{
#ifndef DISTRIBUTION
  char buf[100];

        checkpointer (msg, ptr);
        if (!ptr)
                return;
        if (debug) {
                fprintf (stderr, msg);
                dumpitem (ptr);
        }
        if (((typeitemheader *)ptr)->itemid < TEXTID || ((typeitemheader *)ptr)->itemid > SPORGLID) {
                fprintf (stderr, msg);
                gerror ("Bad itemtype\n");
        }
        /*checkpointer (sprintf (buf, "%s ptr->next: ", msg), ((typeitemheader *)ptr)->next);*/
        if (((typeitemheader *)ptr)->itemid == VSPANID) {
                if (((typevspan *)ptr)->stream.mantissa[0] != 1 && ((typevspan *)ptr)->stream.mantissa[0] != 2) {
                        fprintf (stderr, msg);
                        puttumbler (stderr, &((typevspan *)ptr)->stream);
                        fprintf (stderr, "  ");
                        gerror ("Bad span stream address.\n");
                }
        }
        if (((typeitemheader *)ptr)->itemid == VSPECID) {
                checkitem (msg, ((typevspec *)ptr)->vspanset);
                if (((typevspec *)ptr)->vspanset->itemid != VSPANID)
                        gerror ("vspanset doesn't have proper itemid.\n");
        }
#endif
}

int checkpointer(char *msg, char *ptr)
{
return;       /*
        if (!ptr) {
                if (debug) {
                        fprintf (stderr, msg);
                        fprintf (stderr, "NULL pointer\n");
                } 
                return;
        }
        if (((unsigned)ptr) & 1) {
                fprintf (stderr, msg);
                gerror ("Pointer non-aligned.\n");
        }
        if (ptr > (char *) 0x1bffff) {
                fprintf (stderr, msg);
                if (ptr < (char *) 0x1e0000)
                        fprintf (stderr, "Pointer in framebuffer\n");
                gerror ("Pointer in high-mem\n");
        }
        if (ptr < (char *) 0x40000) {
                fprintf (stderr, msg);
                gerror ("Pointer to hardware protected low memory.\n");
        }
        if (ptr < &end//etext//) {
                fprintf (stderr, msg);
                gerror ("Pointer below end\n");
        }
*/
}

int dumpspanpairset(typespanpairset spanpairset)
{
#ifndef DISTRIBUTION
        for (; spanpairset; spanpairset = spanpairset->nextspanpair)
                dumpspanpair ( spanpairset);
#endif
}

int dumpspanpair(typespanpair *spanpair)
{
#ifndef DISTRIBUTION
        fprintf (stderr, "stream1:  ");
        dumptumbler ( &spanpair->stream1);
        fprintf (stderr, "\nstream2:  ");
        dumptumbler ( &spanpair->stream2);
        fprintf (stderr, "\nwidth:  ");
        dumptumbler ( &spanpair->widthofspan);
        fprintf (stderr, "\n");
#endif
}
int dumphexstuff(char *ptr)
{
#ifndef DISTRIBUTION
  int i;
	fprintf(stderr,"\n");

	for(i=0;i<120;i++){

		fprintf(stderr,"%x ",*(ptr+i)&0xff);
	}
	fprintf(stderr,"\n");
#endif
}

int checknumofsons(typecuc *ptr)
{
#ifndef DISTRIBUTION
  int i;
  typecuc *np;
	i = 0;
	if(!ptr||!ptr->height)
		return;
	for(np= (typecuc *)ptr->leftson;np;np=(typecuc *)np->rightbro,i++)
		;
	if(i!=ptr->numberofsons){
dumpsubtree(ptr);
fprintf(stderr,"i = %d numberofsons = %d\n",i, ptr->numberofsons);
		for(np= (typecuc *)ptr->leftson;np;np=(typecuc *)np->rightbro,i++){
		/*	dump(np)*/;
		}
	/*	gerror(*/fprintf(stderr,"numberofson mismach in checknumofsons\n");
	}
#endif
}

int nchecknumofsons(typecuc *ptr)
{
#ifndef DISTRIBUTION
  int i;
  typecuc *np;
	i = 0;
	if(!ptr||!ptr->height)
		return;
	for(np= (typecuc *)ptr->leftson;np;np=(typecuc *)np->rightbro,i++)
		;
	if(i!=ptr->numberofsons){
dumpsubtree(ptr);
fprintf(stderr,"i = %d numberofsons = %d\n",i, ptr->numberofsons);
		for(np= (typecuc *)ptr->leftson;np;np=(typecuc *)np->rightbro,i++){
		/*	dump(np)*/;
		}
		/*gerror(*/fprintf(stderr,"numberofson mismach in nchecknumofsons\n");
	}
#endif
}
