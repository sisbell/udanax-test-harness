/* Copyright � 1979-1999 Udanax.com. All rights reserved.

* This code is licensed under the terms of The Udanax Open-Source License, 
* which contains precisely the terms of the X11 License.  The full text of 
* The Udanax Open-Source License can be found in the distribution in the file 
* license.html.  If this file is absent, a copy can be found at 
* http://udanax.xanadu.com/license.html and http://www.udanax.com/license.html
*/
/* xudo1.d - Udanax document handling routines */

#include "xanadu.h"
#include "players.h"


bool dofinddocscontaining(typetask *taskptr, typespecset specset, typelinkset *addresssetptr)
{
  typeispanset ispanset;
  bool specset2ispanset(), finddocscontainingsp();

	return (
	   specset2ispanset (taskptr, specset, &ispanset,NOBERTREQUIRED)
	&& finddocscontainingsp (taskptr, ispanset, addresssetptr));
}

bool doappend(typetask *taskptr, typeisa *docptr, typetextset textset)
{
  bool appendpm(),insertspanf(); /*zzz dies this put in granf?*/

	return (appendpm (taskptr, docptr, textset)/*&&
       appendpm includes insertspanf!	 insertspanf(taskptr,spanf,docptr,textset,DOCISPAN)*/
	);
}

bool dorearrange(typetask *taskptr, typeisa *docisaptr, typecutseq *cutseqptr)
{
  typeorgl docorgl;
  bool findorgl(), rearrangepm();;

	return (
	   findorgl (taskptr, granf, docisaptr, &docorgl, WRITEBERT)
	&& rearrangepm (taskptr, docisaptr, docorgl, cutseqptr)
	/*&& TRUE*/ /* ht stuff */  );
}

bool docopy(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typespecset specset)
{
  typeispanset ispanset;
/*  typeisa htisa;      */
  typeorgl docorgl;
  bool specset2ispanset(), findorgl(), acceptablevsa(), insertpm(), insertspanf();
  bool asserttreeisok();

	return (
	   specset2ispanset (taskptr, specset, &ispanset, NOBERTREQUIRED)
	&& findorgl (taskptr, granf, docisaptr, &docorgl, WRITEBERT)
	&& acceptablevsa (vsaptr, docorgl)
	&& asserttreeisok(docorgl)

	/* the meat of docopy: */
	&& insertpm (taskptr, docisaptr, docorgl, vsaptr, ispanset)

	&&  insertspanf (taskptr, spanf, docisaptr, ispanset, DOCISPAN)
	&& asserttreeisok(docorgl)
/*      &&  ht stuff */ );
}
bool docopyinternal(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typespecset specset)
{
  typeispanset ispanset;
/*  typeisa htisa;      */
  typeorgl docorgl;
  bool specset2ispanset(), findorgl(), acceptablevsa(), insertpm(), insertspanf();
  bool asserttreeisok();

	if (!specset2ispanset (taskptr, specset, &ispanset, NOBERTREQUIRED)) return FALSE;
	if (!findorgl (taskptr, granf, docisaptr, &docorgl, NOBERTREQUIRED)) return FALSE;
	if (!acceptablevsa (vsaptr, docorgl)) return FALSE;
	if (!asserttreeisok(docorgl)) return FALSE;
	if (!insertpm (taskptr, docisaptr, docorgl, vsaptr, ispanset)) return FALSE;
	if (!insertspanf (taskptr, spanf, docisaptr, ispanset, DOCISPAN)) return FALSE;
	if (!asserttreeisok(docorgl)) return FALSE;
	return TRUE;
}

  typespec spec,spec2,spec3;
  typevstuffset uppervstuffset;
tumbler fivetumbler = {0,0,0,0,500/*100*/,0,0,0,0,0,0,0};
bool doinsert(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typetextset textset)
{
  typehint hint;
  typespanset ispanset;
/* these defs for debug*/
/*  typespan thisspan;*/
  INT ret;
/*  INT temp;*/
  bool doretrievev(), inserttextingranf(), docopy();

/*if(debug){ 
debug = FALSE;
spec.docisa = *docisaptr;
((typeitemheader)spec).next = NULL;
spec.itemid = VSPECID;
spec.vspanset = &thisspan;
thisspan.itemid = VSPANID;
thisspan.next = NULL;
temp = vsaptr->mantissa[1];
thisspan.stream = *vsaptr;
thisspan.width = fivetumbler;
spec.vspanset->stream.mantissa[1] =1// +=5//;
copyspecset(taskptr,&spec,&spec2);
copyspecset(taskptr,&spec,&spec3);
spec3.vspanset->stream.mantissa[1] += textset->length;
doretrievev(taskptr,&spec2,&uppervstuffset);
vsaptr->mantissa[1] = temp;
debug = TRUE;
}*/

	makehint(DOCUMENT, ATOM, TEXTATOM, docisaptr, &hint);
	ret = (inserttextingranf(taskptr, granf, &hint, textset, &ispanset)
		&& docopy (taskptr, docisaptr, vsaptr, ispanset)
	/* no ht stuff here, 'cause it's taken care of in */
	/*   docopy */ );
	return(ret);
}

int checkspecandstringbefore(void)
{
return(0);
/*if(debug){ assertspecisstring(&spec2,uppervstuffset->xxtest.string); }*/
}

int copyspecset(typetask *taskptr, typespec *specptr, typespec *newptr)
{
  typespec  *this;
  INT *talloc();
	if(specptr == NULL)
		return(0);
	this = newptr;
	for(;specptr;specptr=(typespec *)((typeitemheader *)specptr)->next,this=(typespec *)talloc(taskptr,sizeof(typespec))){
		*this = *specptr;
		copyspanset (taskptr,((typevspec *)specptr)->vspanset, &((typevspec *)this)->vspanset);
	}
	((typeitemheader *)this) -> next = NULL;
}

int copyspanset(typetask *taskptr, typespan *spanptr, typespan **newptrptr)
{
  typespan  *this;
  INT *talloc();

	this = (typespan *)talloc(taskptr,sizeof(typespan));
	*newptrptr = this;
	for (; spanptr; spanptr = spanptr->next, this->next = (typespan *)talloc(taskptr,sizeof(typespan))) {
		*this = *spanptr;
	}
	this ->next = NULL;
}
 
bool dodeletevspan(typetask *taskptr, typeisa *docisaptr, typevspan *vspanptr)
{
  typeorgl docorgl;
  bool findorgl(), deletevspanpm();

	return (
	   findorgl (taskptr, granf, docisaptr, &docorgl, WRITEBERT)
	&& deletevspanpm (taskptr, docisaptr, docorgl, vspanptr)
	/*&& TRUE*/ /* ht stuff */ );
}

bool domakelink(typetask *taskptr, typeisa *docisaptr, typespecset fromspecset, typespecset tospecset, typeisa *linkisaptr)
{
  typehint hint;
  tumbler linkvsa, fromvsa, tovsa;
  typespanset ispanset;
  typesporglset fromsporglset;
  typesporglset tosporglset;
  typeorgl link;
  bool createorglingranf(), insertendsetsinspanf(), insertendsetsinorgl(), docopy();
  bool tumbler2spanset(), findnextlinkvsa(), findorgl(), specset2sporglset(), setlinkvsas();

	makehint (DOCUMENT, ATOM, LINKATOM, docisaptr, &hint);
	return (
	     createorglingranf (taskptr, granf, &hint, linkisaptr)
	  && tumbler2spanset (taskptr, linkisaptr, &ispanset)
	  && findnextlinkvsa (taskptr, docisaptr, &linkvsa)
	  && docopy (taskptr, docisaptr, &linkvsa, ispanset)
	  && findorgl (taskptr, granf, linkisaptr, &link, WRITEBERT)
	  && specset2sporglset (taskptr, fromspecset, &fromsporglset, NOBERTREQUIRED)
	  && specset2sporglset (taskptr, tospecset, &tosporglset, NOBERTREQUIRED)
	  && setlinkvsas (&fromvsa, &tovsa, NULL)
	  && insertendsetsinorgl (taskptr, linkisaptr, link, &fromvsa, fromsporglset, &tovsa, tosporglset, NULL, NULL)
	  && insertendsetsinspanf (taskptr, spanf, linkisaptr, fromsporglset, tosporglset, NULL)
	);
}

bool docreatelink(typetask *taskptr, typeisa *docisaptr, typespecset fromspecset, typespecset tospecset, typespecset threespecset, typeisa *linkisaptr)
{
  typehint hint;
  tumbler linkvsa, fromvsa, tovsa, threevsa;
  typespanset ispanset;
  typesporglset fromsporglset;
  typesporglset tosporglset;
  typesporglset threesporglset;
  typeorgl link;
  bool createorglingranf(), insertendsetsinspanf(), insertendsetsinorgl(), docopy();
  bool tumbler2spanset(), findnextlinkvsa(), findorgl(), specset2sporglset(), setlinkvsas();

	makehint (DOCUMENT, ATOM, LINKATOM, docisaptr, &hint);
	return (
	     createorglingranf (taskptr, granf, &hint, linkisaptr)
	  && tumbler2spanset (taskptr, linkisaptr, &ispanset)
	  && findnextlinkvsa (taskptr, docisaptr, &linkvsa)
	  && docopy (taskptr, docisaptr, &linkvsa, ispanset)
	  && findorgl (taskptr, granf, linkisaptr, &link,/*WRITEBERT ECH 7-1*/NOBERTREQUIRED)
	  && specset2sporglset (taskptr, fromspecset, &fromsporglset,NOBERTREQUIRED)
	  && specset2sporglset (taskptr, tospecset, &tosporglset,NOBERTREQUIRED)
	  && specset2sporglset (taskptr, threespecset, &threesporglset,NOBERTREQUIRED)
	  && setlinkvsas (&fromvsa, &tovsa, &threevsa)
	  && insertendsetsinorgl (taskptr, linkisaptr, link, &fromvsa, fromsporglset, &tovsa, tosporglset, &threevsa, threesporglset)
	  && insertendsetsinspanf (taskptr, spanf, linkisaptr, fromsporglset, tosporglset, threesporglset)
	);
}

bool dofollowlink(typetask *taskptr, typeisa *linkisaptr, typespecset *specsetptr, INT whichend)
{
  typesporglset sporglset;
  bool link2sporglset(), linksporglset2specset();

	return (
	   link2sporglset (taskptr, linkisaptr, &sporglset, whichend,NOBERTREQUIRED)
	&& linksporglset2specset (taskptr,&((typesporgl *)sporglset)->sporgladdress, sporglset, specsetptr,/* ECH 6-29 READBERT */NOBERTREQUIRED));

}

bool docreatenewdocument(typetask *taskptr, typeisa *isaptr)
{
  typehint hint;
  bool createorglingranf();

	makehint (ACCOUNT, DOCUMENT, 0, &taskptr->account, &hint);
	return (createorglingranf (taskptr, granf, &hint, isaptr));
}

bool docreatenode_or_account(typetask *taskptr, typeisa *isaptr)
{
  typeisa isa;
  typehint hint;
  bool createorglingranf();
  bool result;

	tumblercopy(isaptr, &isa);
	makehint (NODE, NODE, 0, &isa, &hint);
	result = createorglingranf (taskptr, granf, &hint, &isa);
	if (result) {
		/* Copy the newly allocated address back to output parameter */
		tumblercopy(&isa, isaptr);
	}
	return result;
}

bool docreatenewversion(typetask *taskptr, typeisa *isaptr, typeisa *wheretoputit, typeisa *newisaptr)
{
  typehint hint;
  typevspan vspan;
  typevspec vspec;
  tumbler newtp;	/* for internal open */
  bool doretrievedocvspanfoo(), createorglingranf();

	/* ECH 7-13 introduced test for ownership to do right thing for explicit creation
	   of new version of someone else's document */
	if (tumbleraccounteq(isaptr, wheretoputit) && isthisusersdocument(isaptr)) {
		makehint (DOCUMENT, DOCUMENT, 0, isaptr/*wheretoputit*/, &hint);
	} else {
		/* This does the right thing for new version of someone else's document, as it
		   duplicates the behavior of docreatenewdocument */
		makehint (ACCOUNT, DOCUMENT, 0, wheretoputit, &hint);
	}
	if (!createorglingranf(taskptr, granf, &hint, newisaptr)) {
		return (FALSE);
	}

	if (!doretrievedocvspanfoo (taskptr, isaptr, &vspan)) {
		return FALSE;
	}

	vspec.next = NULL;
	vspec.itemid = VSPECID;
	movetumbler(isaptr, &vspec.docisa);
	vspec.vspanset = &vspan;

	/* Skip doopen ownership check - we just created this document so we own it.
	   Add directly to bert table instead. */
	addtoopen(newisaptr, user, TRUE, WRITEBERT);
	docopyinternal(taskptr, newisaptr, &vspan.stream, &vspec);
	/* Mark as modified so removefromopen doesn't delete the newly created version */
	logbertmodified(newisaptr, user);
	doclose(taskptr, newisaptr, user);

	return (TRUE);
}

bool doretrievedocvspanfoo(typetask *taskptr, typeisa *docisaptr, typevspan *vspanptr)
{/* this routine is a kluge not yet kluged*/
  typeorgl docorgl;
  bool findorgl(), retrievedocumentpartofvspanpm();

	return (
	   findorgl (taskptr, granf, docisaptr, &docorgl, NOBERTREQUIRED)
	&& retrievedocumentpartofvspanpm (taskptr, docorgl, vspanptr) );
}


bool doretrievedocvspan(typetask *taskptr, typeisa *docisaptr, typevspan *vspanptr)
{
  typeorgl docorgl;
  bool findorgl(), retrievevspanpm();

	return
	   findorgl (taskptr, granf, docisaptr, &docorgl, READBERT)
	&& retrievevspanpm (taskptr, docorgl, vspanptr);
}

bool doretrievedocvspanset(typetask *taskptr, typeisa *docisaptr, typevspanset *vspansetptr)
{
  typeorgl docorgl;
  bool findorgl(), isemptyorgl(), retrievevspansetpm();

	if (!findorgl (taskptr, granf, docisaptr, &docorgl, READBERT))
		return FALSE;

	if (isemptyorgl (docorgl)) {
		*vspansetptr = NULL;  /* Empty document returns empty vspanset */
		return TRUE;
	}

	return retrievevspansetpm (taskptr, docorgl, vspansetptr);
}

bool doretrievev(typetask *taskptr, typespecset specset, typevstuffset *vstuffsetptr)
{
  typeispanset ispanset;
  bool specset2ispanset(), ispanset2vstuffset();

	return
	   specset2ispanset (taskptr, specset, &ispanset,READBERT)
	&& ispanset2vstuffset (taskptr, granf, ispanset, vstuffsetptr);
}

bool dofindlinksfromtothree(typetask *taskptr, typespecset fromvspecset, typespecset tovspecset, typespecset threevspecset, typeispan *orglrangeptr, typelinkset *linksetptr)
{
  bool findlinksfromtothreesp();

	return findlinksfromtothreesp(taskptr, spanf, fromvspecset, tovspecset, threevspecset, orglrangeptr, linksetptr);
}

bool dofindnumoflinksfromtothree(typetask *taskptr, typespecset *fromvspecset, typespecset *tovspecset, typespecset *threevspecset, typeispan *orglrangeptr, INT *numptr)
{
  bool findnumoflinksfromtothreesp();

	return findnumoflinksfromtothreesp (taskptr, spanf, fromvspecset, tovspecset, threevspecset, orglrangeptr, numptr);
}

bool dofindnextnlinksfromtothree(typetask *taskptr, typevspec *fromvspecptr, typevspec *tovspecptr, typevspec *threevspecptr, typeispan *orglrangeptr, typeisa *lastlinkisaptr, typelinkset *nextlinksetptr, INT *nptr)
{
  bool findnextnlinksfromtothreesp();

	return findnextnlinksfromtothreesp (taskptr, fromvspecptr, tovspecptr, threevspecptr, orglrangeptr, lastlinkisaptr, nextlinksetptr, nptr);
}

bool doretrieveendsets(typetask *taskptr, typespecset specset, typespecset *fromsetptr, typespecset *tosetptr, typespecset *threesetptr)
{
  bool retrieveendsetsfromspanf();

	 return retrieveendsetsfromspanf(taskptr, specset, fromsetptr, tosetptr, threesetptr);
}


/* Bug 009 SEMANTIC FIX: Filter vspanset to text subspace only (V >= 1.0).
 *
 * compare_versions finds content with "common origin" - shared permascroll
 * identity. Link references at V-position 0.x are document metadata, not
 * transcludable content. They have unique ISAs, not permascroll addresses,
 * so comparing them is semantically undefined.
 *
 * See Finding 015: Semantic Definition of compare_versions
 */
typevspanset filter_vspanset_to_text_subspace(typetask *taskptr, typevspanset vspanset)
{
  typevspanset result = NULL;
  typevspanset *resultptr = &result;
  tumbler text_subspace_start;
  INT *taskalloc();

	/* Create tumbler for 1.0 (start of text subspace) */
	tumblerclear(&text_subspace_start);
	tumblerincrement(&text_subspace_start, 0, 1, &text_subspace_start);

	/* Copy only spans where stream >= 1.0 */
	for (; vspanset; vspanset = vspanset->next) {
		if (tumblercmp(&vspanset->stream, &text_subspace_start) >= EQUAL) {
			/* This span is in text subspace - keep it */
			*resultptr = (typevspanset)taskalloc(taskptr, sizeof(typevspan));
			(*resultptr)->itemid = VSPANID;
			movetumbler(&vspanset->stream, &(*resultptr)->stream);
			movetumbler(&vspanset->width, &(*resultptr)->width);
			(*resultptr)->next = NULL;
			resultptr = &(*resultptr)->next;
		}
		/* Spans with stream < 1.0 are in link subspace - skip them */
	}
	return result;
}

/* Filter all vspansets in a specset to text subspace only */
void filter_specset_to_text_subspace(typetask *taskptr, typespecset specset)
{
  typevspec *vspec;
  typevspanset filtered;

	for (; specset; specset = (typespecset)((typeitemheader *)specset)->next) {
		vspec = (typevspec *)specset;
		filtered = filter_vspanset_to_text_subspace(taskptr, vspec->vspanset);
		/* Note: We don't free the old vspanset here as it may be shared.
		 * The task allocator will clean up when the task completes. */
		vspec->vspanset = filtered;
	}
}

bool doshowrelationof2versions(typetask *taskptr, typespecset version1, typespecset version2, typespanpairset *relation)
{
  typeispanset version1ispans = NULL;
  typeispanset version2ispans = NULL;
  typeispanset commonispans = NULL;
  bool specset2ispanset();
  bool intersectspansets();
  bool ispansetandspecsets2spanpairset();

	/* SEMANTIC FIX: Filter to text subspace before comparison.
	 * Link references (V < 1.0) are not content with "common origin".
	 * See Finding 015 for the semantic definition. */
	filter_specset_to_text_subspace(taskptr, version1);
	filter_specset_to_text_subspace(taskptr, version2);

	return
		specset2ispanset(taskptr, version1, &version1ispans, READBERT)
	  &&    specset2ispanset(taskptr, version2, &version2ispans, READBERT)
	  &&    intersectspansets(taskptr, version1ispans, version2ispans, &commonispans, ISPANID)
	  &&    ispansetandspecsets2spanpairset(taskptr, commonispans, version1, version2, relation)
	;
}

 
/* --------------- punt line ----------------- */

/* donavigateonht */
