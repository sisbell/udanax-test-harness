/* Copyright � 1979-1999 Udanax.com. All rights reserved.

* This code is licensed under the terms of The Udanax Open-Source License, 
* which contains precisely the terms of the X11 License.  The full text of 
* The Udanax Open-Source License can be found in the distribution in the file 
* license.html.  If this file is absent, a copy can be found at 
* http://udanax.xanadu.com/license.html and http://www.udanax.com/license.html
*/
/* tumble.d -  tumbler arithmetic routines */

#include "common.h"	/* EXTERNAL VARIABLE BEWARE!!*/

/* Forward declarations for debug functions */
#ifndef DISTRIBUTION
extern int dump(void *ptr);
extern int dumpwholetree(void *ptr);
#endif

tumbler ZEROTUMBLERvar;
static INT abscmp();

/* ---------------- Routines to test tumblers -------------- */

bool tumblereq(tumbler *a, tumbler *b)
{
  register INT i;
       /* Use field-by-field comparison to avoid issues with struct padding */
       if (a->xvartumbler != b->xvartumbler) return FALSE;
       if (a->varandnotfixed != b->varandnotfixed) return FALSE;
       if (a->sign != b->sign) return FALSE;
       if (a->exp != b->exp) return FALSE;
       for (i = 0; i < NPLACES; i++) {
               if (a->mantissa[i] != b->mantissa[i]) return FALSE;
       }
       return TRUE;
}

bool tumbleraccounteq(tumbler *aptr, tumbler *bptr)
{
  INT i, j_b;

	/* Check if sign matches */
	if (aptr->sign != bptr->sign) {
		return(FALSE);
	}

	/* Compare until account (bptr) terminates with two zeros.
	   Document (aptr) may continue beyond the account's address space.

	   Key insight: When account has a zero, it marks the boundary of the
	   account's address space. The document can have any value there
	   (continuing to sub-addresses). We only check for exact match on
	   non-zero account positions. */
	for (j_b = 0, i = 0; i < NPLACES; i++) {
		if (bptr->mantissa[i] == 0) {
			/* Account has a zero - check if it's the terminator (second zero) */
			if (++j_b == 2) {
				return(TRUE);  /* Account terminated, document is under this account */
			}
			/* First zero in account - document can have any value here
			   (it may be continuing to a sub-address). Skip mismatch check. */
		} else {
			/* Account has non-zero - document must match exactly */
			if (aptr->mantissa[i] != bptr->mantissa[i]) {
				return(FALSE);
			}
		}
	}
	return (TRUE);
}

INT tumblercmp(tumbler *aptr, tumbler *bptr)
{
	if (iszerotumbler(aptr)){
		if (iszerotumbler(bptr))
			return (EQUAL);
		else
			return (bptr->sign ? GREATER : LESS);
	}
	if (iszerotumbler(bptr))
		return (aptr->sign ? LESS : GREATER);
	if (aptr->sign == bptr->sign)
		return (aptr->sign ? abscmp(bptr,aptr) : abscmp(aptr,bptr));
	return (aptr->sign ? LESS : GREATER);
}
#ifndef ExPeriMental
static INT abscmp(tumbler *aptr, tumbler *bptr)
{
  register INT *a, *b;
  register INT i, cmp;

	if (aptr->exp != bptr->exp) {
		if (aptr->exp < bptr->exp) {
			return(LESS);
		} else {
			return(GREATER);
		}
	} else {
		a = (INT *) aptr->mantissa;
		b = (INT *) bptr->mantissa;
		for (i = NPLACES; i--;) {
		        if(!(cmp = *a++ - *b++)){
			} else if (cmp < 0) {
				return (LESS);	/* a < b */
			} else {  /* if (cmp > 0) */
				return (GREATER);
			}
		}
	}
	return (EQUAL);
}
#else
static INT abscmp(tumbler *aptr, tumbler *bptr)
{
  register INT *a, *b;
  register INT i, cmp;

	if (aptr->exp != bptr->exp) {
		if (aptr->exp < bptr->exp) {
			return(LESS);
		} else {
			return(GREATER);
		}
	} else {
		a = (INT *) aptr->mantissa;
		b = (INT *) bptr->mantissa;
		for (i = NPLACES; i--;) {
			cmp = *a - *b;
			if (cmp == 0) { /* this is an efficiency hack */
				a++; b++;
				continue;
			} else if (cmp < 0) {
				return (LESS);	/* a < b */
			} else {  /* if (cmp > 0) */
				return (GREATER);
			}
		}
	}
	return (EQUAL);
}

#endif

INT intervalcmp(tumbler *left, tumbler *right, tumbler *address)
{
  register INT cmp;

	cmp = tumblercmp (address, left);
	if (cmp == LESS)
		return (TOMYLEFT);
	  else if (cmp == EQUAL)
		return (ONMYLEFTBORDER);
	cmp = tumblercmp (address, right);
	if (cmp == LESS)
		return (THRUME);
	  else if (cmp == EQUAL)
		return (ONMYRIGHTBORDER);
	  else
		return (TOMYRIGHT);
}

/*  bool
iszerotumbler(tumblerptr)
  tumbler *tumblerptr;
{
	return(!(tumblerptr -> mantissa[0]));
} */

bool tumblercheckptr(tumbler *ptr, INT *crumptr)
{
  bool wrong;
  INT i;
	wrong = FALSE;
	if (ptr->exp > 0){
#ifndef DISTRIBUTION
		fprintf(stderr,"bad exp ");
#endif
		wrong = TRUE;
	}
	if (ptr->sign && ptr->mantissa[0] == 0){
#ifndef DISTRIBUTION
		fprintf(stderr," negative zero ");
#endif
		wrong = TRUE;
	}
	if (ptr->exp && ptr->mantissa[0] == 0){
#ifndef DISTRIBUTION
		fprintf(stderr,"fucked up non-normalized");
#endif
		wrong = TRUE;
	}
	if (ptr->mantissa[0] == 0){
		for (i = 1; i < NPLACES; ++i){
			if (ptr->mantissa[i] != 0){
#ifndef DISTRIBUTION
				fprintf(stderr,"nonzerozerotumbler");
#endif
				wrong = TRUE;
			}
		}
	}
	for (i = 0; i < NPLACES; ++i){
		if ((INT)(ptr->mantissa[i]) < 0){
#ifndef DISTRIBUTION
			fprintf(stderr,"negative digit");
#endif
			wrong = TRUE;
		}
	}
	if (wrong) {
#ifndef DISTRIBUTION
			dumptumbler (ptr);
			if(crumptr){
				dump(crumptr);
			}
			fprintf(stderr,"\n\n invalid tumbler \n\n");
			if(crumptr){
				dumpwholetree(crumptr);
			}
			gerror("  invalid tumbler\n");
#else
	gerror("");
#endif
			return (FALSE);
	}
	return (TRUE);
}

bool tumblercheck(tumbler *ptr)
{
	return(tumblercheckptr(ptr, (INT*) NULL));
}

/* says whether there is no more than a single non-zero
**  digit in mantissa
*/
bool is1story(tumbler *tumblerptr)
{
  INT i;

/*	if (!tumblercheck (tumblerptr))
		qerror ();
*/	for (i = 1; i < NPLACES; i++)
		if (tumblerptr->mantissa[i] != 0)
			return (FALSE);
	return (TRUE);
}

INT nstories(tumbler *tumblerptr)
{
  INT i;

/*	if (!tumblercheck (tumblerptr))
		qerror ();
*/	for (i = NPLACES; i > 0 && tumblerptr->mantissa[--i] == 0;);
	return (i + 1);
}

INT tumblerlength(tumbler *tumblerptr)
{
	return (nstories (tumblerptr) - tumblerptr->exp);
}

/*  INT
nzeroesintumbler (tumblerptr)
  tumbler *tumblerptr;
{
  INT n, i, count;

	n = nstories (tumblerptr);
	for (count = i = 0; i < n; ++i)
		if (tumblerptr->mantissa[i] == 0)
			++count;
	count -= tumblerptr->exp;
	return (count);
}*/

INT lastdigitintumbler(tumbler *tumblerptr)
{
  INT n, digit;

	n = nstories (tumblerptr);
	digit = tumblerptr->mantissa[n -1];
	return (digit);
}

/* --------- Routines below set and change tumblers -------- */

int tumblerjustify(tumbler *tumblerptr)
{
  register INT i, j;
  INT shift;
  tdigit *mantissaptr;
  
	mantissaptr = tumblerptr->mantissa;
	if (mantissaptr[0] != 0) {
		return(0);
	}
	for (shift = 0; mantissaptr[shift] == 0; ++shift) {
		if (shift == NPLACES - 1) {
			tumblerptr->exp = 0;
			tumblerptr->sign = 0;
			return(0);
		}
	}
	for (i = 0, j = shift; j < NPLACES;)
		mantissaptr[i++] = mantissaptr[j++];
	while (i < NPLACES)
		mantissaptr[i++] = 0;
	tumblerptr->exp -= shift;
/*	if (!tumblercheck (tumblerptr))
		qerror ();
*/}

int partialtumblerjustify(tumbler *tumblerptr)
{
  register INT i, j;
  INT shift;
  tdigit *mantissaptr;
  
	mantissaptr = tumblerptr->mantissa;
	/* test commented out because is done before this routine is called for efficiency */
      /*  if (mantissaptr[0] != 0) {
		return(0);
	}*/
	for (shift = 0; mantissaptr[shift] == 0; ++shift) {
		if (shift == NPLACES - 1) {
			tumblerptr->exp = 0;
			tumblerptr->sign = 0;
			return(0);
		}
	}
	for (i = 0, j = shift; j < NPLACES;)
		mantissaptr[i++] = mantissaptr[j++];
	while (i < NPLACES)
		mantissaptr[i++] = 0;
	tumblerptr->exp -= shift;
/*	if (!tumblercheck (tumblerptr))
		qerror ();
*/}

int tumblercopy(tumbler *fromptr, tumbler *toptr)
{
	/*movmem (fromptr, toptr, sizeof(tumbler));  */
	movetumbler(fromptr,toptr); 
}

/*tumblermin (aptr, bptr, cptr)
 register  tumbler *aptr, *bptr, *cptr;
{
	if (tumblercmp (aptr, bptr) == LESS)
		movetumbler (aptr, cptr);
	  else
		movetumbler (bptr, cptr);
}*/

int tumblermax(tumbler *aptr, tumbler *bptr, tumbler *cptr)
{
	if (tumblercmp (aptr, bptr) == GREATER)
		movetumbler (aptr, cptr);
	  else
		movetumbler (bptr, cptr);
}

int functiontumbleradd(tumbler *aptr, tumbler *bptr, tumbler *cptr)  /* tumbler add is ~50% of cpu so has been */
			       /*tightened somewhat */
{
	if (iszerotumbler(bptr)){
		movetumbler (aptr, cptr);
		return(0);
	  }else if (iszerotumbler(aptr)){
		movetumbler (bptr, cptr);
		return(0);
	  }else if (aptr->sign == bptr->sign) {
		absadd (aptr, bptr, cptr);
		cptr->sign = aptr->sign;
		/*absadd returns justified result so no need to justify*/
		/* I'm not so sure of the subtracts, they aren't used much*/
		/*
		if(cptr->mantissa[0] == 0){
			partialtumblerjustify (cptr);
		}
		*/
	} else if (abscmp (aptr, bptr) == GREATER) {
		strongsub (aptr, bptr, cptr);
		cptr->sign = aptr->sign;
		if(cptr->mantissa[0] == 0){
			partialtumblerjustify (cptr);
		}
	} else {
		weaksub (bptr, aptr, cptr);
		cptr->sign = bptr->sign;
		if(cptr->mantissa[0] == 0){
			partialtumblerjustify (cptr);
		}
	}
/*	tumblercheck (cptr);*/
/*
	if (cptr->sign) {
		fprintf(stderr,"TUMBLERADD NEGATIVE OUTPUT\n");
		dumptumbler(cptr);
		fprintf(stderr,"\n");
	}
*/}

int tumblersub(tumbler *aptr, tumbler *bptr, tumbler *cptr)
{
  tumbler temp;
/*
	if(aptr->sign || bptr->sign) {
		fprintf(stderr,"TUMBLERSUB NEG IN \n");
		dumptumbler(aptr);
		fprintf(stderr,"   ");
		dumptumbler(bptr);
		fprintf(stderr,"\n");
	}
*/
	if (iszerotumbler (bptr))
		movetumbler (aptr, cptr);
	else if (tumblereq (aptr, bptr))
		tumblerclear (cptr);
	else if (iszerotumbler (aptr)) {
		movetumbler (bptr, cptr);
		cptr->sign = !cptr->sign;
	} else {
		movetumbler (bptr, &temp);
		temp.sign = !temp.sign;
		tumbleradd (aptr, &temp, cptr);
	}
	tumblerjustify (cptr);
/*	tumblercheck (cptr);*/
/*
	if (cptr->sign) {
		fprintf(stderr,"TUMBLERSUB NEGATIVE OUTPUT\n");
		dumptumbler(cptr);
		fprintf(stderr,"\n");
	}
*/

} 
#ifndef ExPeRiMENATL
#endif

int absadd(tumbler *aptr, tumbler *bptr, tumbler *cptr)
{
  register INT i, j;
  INT place;
  INT temp;
  register tdigit *ansmant;
  register tdigit *bmant, *amant;
  tumbler answer;		      

	i = j = 0;
	amant = aptr->mantissa;
	bmant = bptr->mantissa;
	answer.xvartumbler = 0;
	answer.varandnotfixed = 0;
	answer.sign = 0;
	ansmant = answer.mantissa;
	if (aptr->exp == bptr->exp) {
		answer.exp = aptr->exp;
		ansmant[0] = amant[0] + bmant[0];
		i = j = 1;
	} else if (aptr->exp > bptr->exp) {
		answer.exp = aptr->exp;
		temp = aptr->exp-bptr->exp;
		while ( i < temp ) {
			ansmant[j++] = amant[i++];
		}
		ansmant[j++] = amant[i++] + bmant[0];
		i = 1;
	} else {
		answer.exp = bptr->exp;
		temp = bptr->exp - aptr->exp;
		while (i <= temp) {
			ansmant[j++] = bmant[i++];
		}
	}

	while ( j <= NPLACES -1 ) {    
		ansmant[j++] = bmant[i++];
	}	 
	movetumbler (&answer, cptr);
	return(0);
}

#ifdef  OlDVeRsIon
int absadd(tumbler *aptr, tumbler *bptr, tumbler *cptr)
{
  register INT i, j;
  INT place;
  INT temp;
  register tdigit *ansmant;
  register tdigit *bmant, *amant;
  tumbler answer;		      

	i = j = 0;
	amant = aptr->mantissa;
	bmant = bptr->mantissa;
	tumblerclear (&answer);
	ansmant = answer.mantissa;
	if (aptr->exp == bptr->exp) {
		answer.exp = aptr->exp;
		ansmant[0] = amant[0] + bmant[0];
		i = j = 1;
	} else if (aptr->exp > bptr->exp) {
		answer.exp = aptr->exp;
		temp = aptr->exp-bptr->exp;
		while ( i < temp ) {
			ansmant[j++] = amant[i++];
		}
		ansmant[j++] = amant[i++] + bmant[0];
		i = 1;
	} else {
		answer.exp = bptr->exp;
		temp = bptr->exp - aptr->exp;
		while (i <= temp) {
			ansmant[j++] = bmant[i++];
		}
	}

	while ( j <= NPLACES -1 ) {    
		ansmant[j++] = bmant[i++];
	}	 
	movetumbler (&answer, cptr);
	return(0);
}
 
#endif




int strongsub(tumbler *aptr, tumbler *bptr, tumbler *cptr)
{
  tumbler answer;
  register INT i, j;

	tumblerclear(&answer);
	if (tumblereq (aptr, bptr)) {
		movetumbler (&answer, cptr);
		return(0);
	}
	if (bptr->exp < aptr->exp) {
		movetumbler(aptr,cptr);
		return(0);
	}
	answer.exp = aptr->exp;
	for (i = 0; aptr->mantissa[i] == bptr->mantissa[i]; ++i) {
		--answer.exp;
		if (i >= NPLACES) {
			movetumbler (&answer, cptr);
			return(0);
		}
	}
	answer.mantissa[0] = aptr->mantissa[i] - bptr->mantissa[i];
	if (++i >= NPLACES) {
		movetumbler (&answer, cptr);
		return(0);
	}
	for (j = 1; j < NPLACES && i < NPLACES;)
		answer.mantissa[j++] = aptr->mantissa[i++];
	movetumbler (&answer, cptr);
	return(0);
}

int weaksub(tumbler *aptr, tumbler *bptr, tumbler *cptr)
{
   tumbler answer;
  register INT i;
  INT expdiff;

	tumblerclear(&answer);
	if (tumblereq (aptr, bptr)) {
		movetumbler (&answer, cptr);
		return(0);
	}
	answer.exp = aptr->exp;
	expdiff = aptr->exp - bptr->exp;
	for (i = 0; i < expdiff; ++i) {
		answer.mantissa[i] = aptr->mantissa[i];
		if (i >= NPLACES) {
			movetumbler (&answer, cptr);
			return(0);
		}
	}
	answer.mantissa[i] = aptr->mantissa[i] - bptr->mantissa[0];
	movetumbler (&answer, cptr);
}

INT tumblerintdiff(tumbler *aptr, tumbler *bptr)
{
  tumbler c;

	tumblersub (aptr, bptr, &c);
	return (c.mantissa[0]);
}

int tumblerincrement(tumbler *aptr, INT rightshift, INT bint, tumbler *cptr)
{
  register INT idx;

	if (iszerotumbler (aptr)) {
		tumblerclear (cptr);
		cptr->exp = -rightshift;
		cptr->mantissa[0] = bint;
		return(0);
	}
	if (aptr != cptr)
		movetumbler(aptr,cptr);
	for (idx = NPLACES ; aptr->mantissa[--idx] == 0 && idx > 0;);
	if (idx + rightshift >= NPLACES) {
#ifndef DISTRIBUTION
		dumptumbler (aptr);
		fprintf(stderr," idx = %d  rightshift = %d\n", idx, rightshift);
		gerror ("tumblerincrement overflow\n");
#else
		gerror("");
#endif
	}
	cptr->mantissa[idx + rightshift] += bint;
	tumblerjustify (cptr);
}

int tumblertruncate(tumbler *aptr, INT bint, tumbler *cptr)
{
  tumbler answer;
  INT i;

	movetumbler (aptr, &answer);
	for  (i = answer.exp; i < 0 && bint > 0; ++i, --bint);
	if (bint <= 0)
		tumblerclear (&answer);
	  else
		for (; bint < NPLACES; ++bint)
			answer.mantissa[bint] = 0;
	tumblerjustify (&answer);
	movetumbler (&answer, cptr);
}

int prefixtumbler(tumbler *aptr, INT bint, tumbler *cptr)
{
  tumbler temp1, temp2;

	tumblerclear (&temp1);
	temp1.mantissa[0] = bint;
	movetumbler (aptr, &temp2);
	if (!iszerotumbler (&temp2)) /* yuckh! */
		temp2.exp -= 1;
	tumbleradd (&temp1, &temp2, cptr);
}

/*
int beheadtumbler(tumbler *aptr, tumbler *bptr)
{
  tumbler temp;
  INT i;

	movetumbler (aptr, &temp);
	if (temp.exp < 0)
		++temp.exp;
	  else {
		for (i = 0; i < NPLACES-1; ++i)
			temp.mantissa[i] = temp.mantissa[i+1];
		temp.mantissa[NPLACES-1] = 0;
	}
	tumblerjustify (&temp);
	movetumbler (&temp, bptr);
}
*/


int beheadtumbler(tumbler *aptr, tumbler *bptr)
{
  tumbler temp;

	movetumbler (aptr, &temp);
	++temp.exp;
	if (aptr->exp == 0)
		temp.mantissa[0] = 0;
	tumblerjustify (&temp);
	movetumbler (&temp, bptr);
}

int docidandvstream2tumbler(tumbler *docid, tumbler *vstream, tumbler *tumbleptr)
{
  INT i, j;

	movetumbler (docid, tumbleptr);
	for (i = NPLACES-1; i >= 0; i--) {
		if (tumbleptr->mantissa[i]) {
			++i;
			break;
		}
	}
	for (j = 0; i < NPLACES && j < NPLACES;) {
		tumbleptr->mantissa[++i] = vstream->mantissa[j++];
	}
}

/*
tumblerclear(tumblerptr)
  tumbler *tumblerptr;
{
  static tumbler tumblerzero = 0;
	*tumblerptr = tumblerzero;// uses struct assignment in some compilers//
if (!iszerotumbler(tumblerptr))
  gerror("settumblertozero don't work\n");
}
*/
/*
tumblerclear (tumblerptr)
  tumbler *tumblerptr;
{
//	setmem (tumblerptr, sizeof (tumbler), 0);//
	clear (tumblerptr, sizeof (tumbler));
} 
*/




