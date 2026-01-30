/* Copyright � 1979-1999 Udanax.com. All rights reserved.

* This code is licensed under the terms of The Udanax Open-Source License, 
* which contains precisely the terms of the X11 License.  The full text of 
* The Udanax Open-Source License can be found in the distribution in the file 
* license.html.  If this file is absent, a copy can be found at 
* http://udanax.xanadu.com/license.html and http://www.udanax.com/license.html
*/

/* Routines for comparing versions --- lower level */

#include "xanadu.h"

/* Bug 009 fix: Handle NULL results from restrictvspecsetovercommonispans gracefully.
 * When comparing versions of documents with links, the link subspace spans may not
 * produce any matching ispans, resulting in NULL specsets. Previously this would crash.
 */
int restrictspecsetsaccordingtoispans(typetask *taskptr, typeispanset ispanset, typespecset *specset1, typespecset *specset2)
{
  typespecset s1;
  typespecset s2;
#ifndef DISTRIBUTION
fooitemset("entering retrievespecsetsaccordingtoispans \n",*specset1);
fooitemset("\n specset2 = \n",*specset2);
#endif
	restrictvspecsetovercommonispans (taskptr, ispanset, *specset1, &s1);
/*	removespansnotinoriginal (taskptr, *specset1, &s1);	*/
	/* Bug 009 fix: Only call removespansnotinoriginal if s1 is not NULL */
	if (s1 && *specset1) {
		removespansnotinoriginal (taskptr, s1, specset1);
	}
	if (s1) {
		tfreeitemset (taskptr, (typeitemset)s1);
	}
/*	*specset1 = s1;       */
	restrictvspecsetovercommonispans (taskptr, ispanset, *specset2, &s2);
/*	removespansnotinoriginal (taskptr, *specset2, &s2);	*/
	/* Bug 009 fix: Only call removespansnotinoriginal if s2 is not NULL */
	if (s2 && *specset2) {
		removespansnotinoriginal (taskptr, s2, specset2);
	}
	if (s2) {
		tfreeitemset (taskptr, (typeitemset)s2);
	}
/*	*specset2 = s2;       */
#ifndef DISTRIBUTION
fooitemset("leaving retrievespecsetsaccordingtoispans \n",*specset1);
fooitemset("\n specset2 = \n",*specset2);
#endif
}

int restrictvspecsetovercommonispans(typetask *taskptr, typeispanset ispanset, typespecset specset, typespecset *newspecsetptr)
{
  typeorgl versionorgl;
  typevspec *s1;
  typevspanset docvspanset, *ispan2vspanset();
  INT *taskalloc();
  bool findorgl();
#ifndef DISTRIBUTION
fooitemset("entering restrictspecsetovercommonispans \n",ispanset);
fooitemset("\nspecset = \n",specset);
#endif

	*newspecsetptr = NULL;
	for (; ispanset; ispanset = ispanset->next) {
	     for (; specset; specset = (typespecset)((typeitemheader *)specset)->next) {
		 if(!findorgl(taskptr,granf,&((typevspec *)specset)->docisa,&versionorgl,READBERT))
#ifndef DISTRIBUTION
			 gerror ("restrictvspecset\n");
#else
	gerror("");
#endif
		 docvspanset = NULL;
		 if(ispan2vspanset(taskptr,versionorgl,ispanset,&docvspanset)){
			 s1=(typevspec *)taskalloc(taskptr,sizeof(typevspec ));
			 s1->itemid = VSPECID;
			 *newspecsetptr = (typespecset)s1;
			 movetumbler (&((typevspec *)specset)->docisa, &s1->docisa);
			 s1->vspanset = docvspanset;
			 newspecsetptr = (typespecset *)&s1->next;
		 }
	     }
	}
	*newspecsetptr = NULL;
#ifndef DISTRIBUTION
fooitemset("leaving restrictspecsetovercommonispans \n",ispanset);
fooitemset("\nspecset = \n",specset);
fooitemset("\n newspecset = \n",*newspecsetptr);
#endif
}

int removespansnotinoriginal(typetask *taskptr, typespecset original, typespecset *newptr)
{
  typespecset old;
  typespecset new;
  typevspanset newspanset;
  typevspec *okspec, *first, **nextptr;
  INT *taskalloc();
  bool intersectspansets();
#ifndef DISTRIBUTION
foo("entering removespansnotinoriginal\n");
#endif
	if (!newptr || !*newptr || !original)
#ifndef DISTRIBUTION
		gerror ("Bad removespans call\n");
#else
	gerror("");
#endif

	first = NULL;
	nextptr = NULL;
	for (new = *newptr; new; new = (typespecset)((typeitemheader *)new)->next) {
		for (old = original; old; old = (typespecset)((typeitemheader *)old)->next) {
			if (tumblercmp (&((typevspec *)new)->docisa, &((typevspec *)old)->docisa))
				continue;
			if (intersectspansets (taskptr, ((typevspec *)new)->vspanset, ((typevspec *)old)->vspanset, &newspanset, VSPANID)) {
				okspec=(typevspec*)taskalloc(taskptr,sizeof(typevspec));
				okspec->itemid = VSPECID;
				movetumbler (&((typevspec *)new)->docisa, &okspec->docisa);
				okspec->vspanset = newspanset;
				if (!first)
					first = okspec;
				else
					*nextptr = okspec;
				nextptr = &okspec->next;
			}
		}
	} 
	tfreeitemset (taskptr, (typeitemset)*newptr);
	*nextptr = NULL;
	*newptr = (typespecset)first;
#ifndef DISTRIBUTION
fooitemset("leaving removespansnotinoriginal\n",*newptr);
#endif
}

/* intersectspansets: Find the intersection of two span sets.
 * Returns TRUE if successful (even if result is empty).
 * set1 and set2 are input spansets; set3 points to the result.
 *
 * Bug 009 fix: NULL inputs are now handled gracefully - they produce an empty
 * result rather than crashing. This is important when comparing documents that
 * contain links, as the link subspace (position 0) spans may not convert to ispans.
 */
bool intersectspansets(typetask *taskptr, typespanset set1, typespanset set2, typespanset *set3, INT spantype)
{
  typespan *p;
  bool comparespans();
#ifndef DISTRIBUTION
foo("entering intersectspansets");
#endif

	/* Output pointer must not be NULL */
	if (!set3)
#ifndef DISTRIBUTION
		gerror ("intersectspansets called with NULL output pointer\n");
#else
		gerror("");
#endif

	*set3 = NULL;

	/* If either input is NULL/empty, intersection is empty - return success */
	if (!set1 || !set2) {
#ifndef DISTRIBUTION
foo("intersectspansets: one or both inputs NULL, returning empty result");
#endif
		return (TRUE);
	}

#ifndef DISTRIBUTION
foo("dumping set1\n");
foospanset("",set1);
foo("dumping set2\n");
foospanset("",set2);
#endif
	for (; set1; set1 = set1->next) {
		for (p = set2; p; p = p->next) {
			if (comparespans (taskptr, set1, p, set3, spantype))
				set3 = &(*set3)->next;
		}
	}
#ifndef DISTRIBUTION
foo("leaving intersectspansets");
foo("dumping set3\n");
foospanset("",set3);
#endif
	return (TRUE);
}

bool comparespans(typetask *taskptr, typespan *span1, typespan *span2, typespan **span3, INT spantype)
{
  INT *taskalloc();
  bool spanintersection();

	if (iszerotumbler (&span1->width) || iszerotumbler (&span2->width))
		return (FALSE);
	*span3 = (typespan *) taskalloc (taskptr, sizeof (typespan ));
	(*span3)->itemid = spantype;
	(*span3)->next = NULL;
	if (spanintersection (span1, span2, *span3))
		return (TRUE);
	else {
		tfreeexplicit (taskptr, (char*)*span3);
		*span3 = NULL;
		return (FALSE);
	}
}

bool spanintersection(typespan *aptr, typespan *bptr, typespan *cptr)
{
  tumbler aend, bend;

	tumblerclear (&cptr->stream);
	tumblerclear (&cptr->width);
	tumbleradd (&bptr->stream, &bptr->width, &bend);
	if (tumblercmp (&aptr->stream, &bend) >= EQUAL)
		return (FALSE);
	tumbleradd (&aptr->stream, &aptr->width, &aend);
	if (tumblercmp (&bptr->stream, &aend) >= EQUAL)
		return (FALSE);
/* these following assignments are clearly wrong 12/4/84 */
	switch (tumblercmp (&aptr->stream, &bptr->stream)) {
	  case EQUAL:/* this ones probably ok*/
		movetumbler (&aptr->stream, &cptr->stream);
		switch (tumblercmp (&aend, &bend)) {
		  case EQUAL:
		  case LESS:
			movetumbler (&aptr->width, &cptr->width);
			break;
		  case GREATER:
			movetumbler (&bptr->width, &cptr->width);
		}
		break;
	  case GREATER:
		movetumbler (&aptr->stream, &cptr->stream);
		switch (tumblercmp (&aend, &bend)) {
		  case EQUAL:
		  case LESS:/*ok*/
			movetumbler (&aptr->width, &cptr->width);
			break;	     
		  case GREATER:/*????*/
			tumblersub(&bend,&aptr->stream,&cptr->width);
			/*movetumbler (&bptr->width, &cptr->width);*/
		}
		break;
	  case LESS:
		movetumbler (&bptr->stream, &cptr->stream);
		switch (tumblercmp (&aend, &bend)) {
		  case EQUAL:
		  case GREATER:/*ok*/
			movetumbler (&bptr->width, &cptr->width);
			break;
		  case LESS:/*???*/
			tumblersub(&aend,&bptr->stream,&cptr->width);
			/*movetumbler (&aptr->width, &cptr->width);*/
		}
	}
#ifndef DISTRIBUTION
foospan("in spanintersection \n aspan = ",aptr);
foospan("\n bspan = ",bptr);
foospan("\n cspan = ",cptr);
#endif
	return (TRUE);
}

int makespanpairset(typetask *taskptr, typeispanset ispanset, typespecset specset1, typespecset specset2, typespanpairset *pairsetptr)
{
  tumbler iwidth;
  typespanpairset pairset;
#ifndef DISTRIBUTION
foo("entering makespanpairset");
fooitemset("ispanset = \n",ispanset);
fooitemset("specset1 = \n",specset1);
fooitemset("specset2 = \n",specset2);
#endif
	*pairsetptr = NULL;
	for (; ispanset; ispanset = ispanset->next) {
		movetumbler (&ispanset->width, &iwidth);
		makespanpairsforispan (taskptr, &iwidth, &specset1, &specset2, &pairset);
		*pairsetptr = pairset;
		pairsetptr = &pairset->nextspanpair;
	}
	*pairsetptr = NULL;
#ifndef DISTRIBUTION
foo("leaving makespanpairset");
#endif
}

int makespanpairsforispan(typetask *taskptr, tumbler *iwidth, typespecset *specset1ptr, typespecset *specset2ptr, typespanpairset *pairsetptr)
{
  typespanpair *makespanpair();
  typevspec *spec1, *spec2;
  typespan *span1, *span2;
  tumbler sum;
  INT cmp;
#ifndef DISTRIBUTION
foo("entering makespanpairsforispan\n");
fooitemset("\n*specset1ptr = \n",*specset1ptr);
fooitemset("\n*specset2ptr = \n",*specset2ptr);
#endif
	*pairsetptr = NULL;
	tumblerclear (&sum);
	spec1 = (typevspec *)*specset1ptr;
	span1 = spec1->vspanset;
	spec2 = (typevspec *)*specset2ptr;
	span2 = spec2->vspanset;
	while (span1 && span2 && tumblercmp (iwidth, &sum) == GREATER) {
		cmp = tumblercmp (&span1->width, &span2->width);
		switch (cmp) {
		  case LESS:
		  case EQUAL:
			*pairsetptr = makespanpair (taskptr, &spec1->docisa, &span1->stream, &spec2->docisa, &span2->stream, &span1->width);
			tumbleradd (&sum, &span1->width, &sum);
			if (cmp == EQUAL)
				span2 = span2->next;
			else {
				tumbleradd (&span2->stream, &span1->width, &span2->stream);
				tumblersub (&span2->width, &span1->width, &span2->width);
			}
			span1 = span1->next;
			break;
		  case GREATER:
			*pairsetptr = makespanpair (taskptr, &spec1->docisa, &span1->stream, &spec2->docisa, &span2->stream, &span2->width);
			tumbleradd (&sum, &span2->width, &sum);
			tumbleradd (&span1->stream, &span2->width, &span1->stream);
			tumblersub (&span1->width, &span2->width, &span1->width);
			span2 = span2->next;
		}
		spec1->vspanset = span1;
		spec2->vspanset = span2;
		if (!span1) {
			spec1 = spec1->next;
			*specset1ptr = (typespecset)spec1;
			if (spec1)
				span1 = spec1->vspanset;
		}
		if (!span2) {
			spec2 = spec2->next;
			*specset2ptr = (typespecset)spec2 ;
			if (spec2)
				span2 = spec2->vspanset;
		}
		pairsetptr = &(*pairsetptr)->nextspanpair;
	}
#ifndef DISTRIBUTION
foo("leaving makespanpairsforispan\n");
#endif
}

typespanpair *makespanpair(typetask *taskptr, tumbler *doc1, tumbler *start1, tumbler *doc2, tumbler *start2, tumbler *width)
{
  typespanpair *spanpair;
  INT *taskalloc();

	spanpair = (typespanpair *) taskalloc (taskptr, sizeof (typespanpair ));
	docidandvstream2tumbler (doc1, start1, &spanpair->stream1);
	docidandvstream2tumbler (doc2, start2, &spanpair->stream2);
	movetumbler (width, &spanpair->widthofspan);
	return (spanpair);
}

INT spansubtract(typespan *aptr, typespan *bptr, typespan *cptr)
{
  INT cmp;

	cmp = tumblercmp (&aptr->width, &bptr->width);
	switch (cmp) {
	  case EQUAL:
		tumblerclear (&cptr->stream);
		tumblerclear (&cptr->width);
		break;
	  case GREATER:
		tumbleradd (&aptr->stream, &bptr->width, &cptr->stream);
		tumblersub (&aptr->width, &bptr->width, &cptr->width);
		break;
	  case LESS:
		tumbleradd (&bptr->stream, &aptr->width, &cptr->stream);
		tumblersub (&bptr->width, &aptr->width, &cptr->width);
	}
	return (cmp);
}
