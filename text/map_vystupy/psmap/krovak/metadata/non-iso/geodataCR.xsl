<?xml version="1.0" encoding="iso-8859-2"?>

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
		version="1.0">

<xsl:output method="html" encoding="iso-8859-2" indent="yes"
	    doctype-public="-//W3C//DTD XHTML 1.0 Transitional//EN"
            doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"/>

<xsl:template match="/">
  <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="cs" lang="cs">
    <head>
       <style type="text/css">
	 body { 
	    background-color: #FFFFFF;
	    margin:           10px; 
	    font-family:      sans-serif, verdana, arial;
	    color:            #000000;
	    text-decoration:  none;
	    font-size:        10pt;
	 }
	 h1 { 
	    color:       black;
	    font-size:   19px; 
	    text-align:  center; 
	 }
	 h2 { 
	    color:       black;
	    font-size:   14px; 
	    font-weight: bold;
	    text-align:  left;
	    margin-left: 5px;
	 }
	 h3 { 
	    color:       black;
	    font-size:   12px; 
	    font-weight: bold;
	    text-align:  left;
	    margin-left: 10px;
	 }
	 table.vrstva {
	    width:           95%;
	    border:          solid 1px #000000;
	    border-collapse: collapse;
	    margin-bottom:   10px;
	 }
	 table.vnitrni {
	    width:           100%;
	    border:          0px;
	    margin:          0px;
	 }
	 td.polozka {
	    border:           solid 1px #000000;
	    border-collapse:  collapse;
	    padding:          3px;
	    font-size:        10pt;
	    width:            15%;
	    background-color: #acacac;
	    text-align:       left;
	 }
	 td.polozka_data {
	    border:           solid 1px #000000;
	    border-collapse:  collapse;
	    padding:          3px;
	    font-size:        10pt;
            text-align:       left;
	 }
	 td.id {
	    border:           solid 1px #000000;
	    border-collapse:  collapse;
	    padding:          3px;
	    font-size:        10pt;
	    background-color: #dbdbdb;	 
            text-align:       left;
	 }
	 td.vnitrni {
	    border:          0px;
	    padding:         0px;
            text-align:      left;
	 }
	 hr {
	    border-bottom: 1px solid black;
	    border-top: 1px;
	    color: black;
	    height: 1px;
	 }
	 a { 
	 color:           #00417e;
	 text-decoration: none; 
	 }
	 a:hover { 
	 color:           #000000;
	 text-decoration: none; 
	 }
       </style>
       <meta http-equiv="Content-Type" 
	     content="text/html; charset=iso-8859-2"/>
      <title><xsl:value-of select="/dataset/@popis"/> -- popis dat</title>
    </head>
    <body>
      <h1><a href="http://gama.fsv.cvut.cz/~grass/geodata_cr/index.phtml"
	     title="Oficiální stránky datasetu">
      <xsl:value-of select="/dataset/@popis"/></a> - popis dat</h1>
      <div align="right">
	<table>
	  <xsl:apply-templates select="dataset/mapset" mode="verze">
	    <xsl:sort select="@id" order="ascending"/>
	  </xsl:apply-templates> 
	</table>
      </div>

      <hr />

      <font style="font-size: 14px;"><b>Obsah datasetu:</b></font>
      <xsl:apply-templates select="dataset/mapset" mode="seznam">
	<xsl:sort select="@id" order="ascending"/>
      </xsl:apply-templates>
      <hr />
      
      <xsl:apply-templates select="dataset/mapset" mode="uplne">
	<xsl:sort select="@id" order="ascending"/>
      </xsl:apply-templates>    
        
      <table class="vnitrni">
	<tr>
	  <td class="vnitrni" style="width: 50%">Valid:
	  <a href="http://validator.w3.org/check/referer" title="Valid XHTML 1.0">XHTML 1.0</a>
	<!--
	  <a href="http://jigsaw.w3.org/css-validator/validator?uri=http://gama.fsv.cvut.cz/~grass/geodata_cr/popis_dat.html" title="Valid CSS">CSS</a>
	-->
	  </td>
	  <td class="vnitrni" style="text-align: right">landa.martin <i>na</i> gmail.com</td>
	</tr>
      </table>
    </body>
  </html>
</xsl:template>

<xsl:template match="vrstva" mode="uplne">
  <div align="center">
  <table class="vrstva">
    <tr>
      <td class="polozka">zkrácený název:</td>
      <xsl:choose>
	<xsl:when test="@stav=0">
	  <td class="id" style="background-color: #c80000">
	    <xsl:apply-templates select="@id"/>
	  </td>
	</xsl:when>
	<xsl:otherwise>
	  <td class="id">
	    <xsl:apply-templates select="@id"/>
	  </td>
	</xsl:otherwise>
      </xsl:choose>
    </tr>
    <tr>
      <td class="polozka">název:</td>
      <td class="polozka_data">
	<xsl:apply-templates select="nazev"/>
      </td>
    </tr>
    <tr>
      <td class="polozka">popis:</td>
      <td class="polozka_data">
	<xsl:value-of select="popis"/>
      </td>
    </tr>
    <tr>
      <td class="polozka">atributy:</td>
      <td class="polozka_data">
	<table class="vnitrni">
	  <xsl:apply-templates select="atributy/atribut"/>
	</table>
      </td>
    </tr>
    <tr>
      <td class="polozka">zdroj:</td>
      <td class="polozka_data">
	<table class="vnitrni">
	  <xsl:apply-templates select="zdroj"/>
	</table>  
      </td>
    </tr>
    <tr>
      <td class="polozka">historie:</td>
      <td class="polozka_data">
	<table class="vnitrni">
	  <xsl:apply-templates select="historie"/>
	</table>
      </td>
    </tr>
  </table>
  </div>
</xsl:template>

<xsl:template match="@id">
  <xsl:variable name="url" select="."/>
  <a name="{$url}"><tt><xsl:value-of select="."/></tt></a>
</xsl:template>

<xsl:template match="nazev">
  <b><xsl:apply-templates/></b>
</xsl:template>

<xsl:template match="atribut">
  <tr>
    <xsl:if test="@kod">
      <td class="vnitrni" style="width: 15%"><i><xsl:value-of select="@kod"/></i></td>
      <td class="vnitrni" style="width: 10px">-</td>
    </xsl:if>
    <td class="vnitrni"><xsl:apply-templates/></td>
  </tr>
</xsl:template>

<xsl:template match="zdroj">
  <xsl:variable name="nazev_url" select="@title"/>
  <xsl:variable name="url" select="."/>
  <tr>
    <xsl:choose>
      <xsl:when test="@pozn">
	<td class="vnitrni">
	  <a href="{$url}" title="{$nazev_url}"><xsl:apply-templates/></a>
	  (<xsl:value-of select="@pozn"/>)
	</td>
      </xsl:when>
      <xsl:otherwise>
	<td class="vnitrni">
	  <a href="{$url}" title="{$nazev_url}"><xsl:apply-templates/></a>
	</td>
      </xsl:otherwise>
    </xsl:choose>
  </tr>
</xsl:template>

<xsl:template match="historie">
  <tr>
    <td class="vnitrni" style="width: 5%"><xsl:apply-templates/></td>
    <td class="vnitrni" style="width: 10px">-</td>
    <td class="vnitrni"><xsl:value-of select="@text"/></td>
  </tr>
</xsl:template>

<xsl:template match="mapa">
  <tt><xsl:apply-templates/></tt>
</xsl:template>

<xsl:template match="vrstva" mode="seznam">
  <xsl:variable name="nazev_url" select="nazev"/>
  <xsl:variable name="url" select="@id"/>
  <xsl:choose>
    <xsl:when test="@stav=0">
      <li>
	<a href="{concat('#', $url)}" title="{$nazev_url}"><xsl:value-of select="@id"/></a>
	[odebráno]
      </li>
    </xsl:when>
    <xsl:otherwise>
      <li><a href="{concat('#', $url)}" title="{$nazev_url}"><xsl:value-of select="@id"/></a></li>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<xsl:template match="dataset/mapset" mode="seznam">
  <h2><xsl:value-of select="@id"/>:</h2>
  <ul>
    <xsl:variable name="rpocet" select="count(rastr//vrstva)"/>
    <xsl:if test="$rpocet!=0">
      <li>rastrové vrstvy (<xsl:value-of select="$rpocet"/>):
      <ul>
	<!--
	    <xsl:for-each select="/dataset/rastr/vrstva">
	    <li><xsl:value-of select="@id"/></li>
	    </xsl:for-each>
	-->
	<xsl:apply-templates select="rastr/vrstva" mode="seznam">
	  <xsl:sort select="@id" order="ascending"/>
	</xsl:apply-templates>
      </ul>
      </li>
    </xsl:if>
    <xsl:variable name="vpocet" select="count(vektor//vrstva)"/>
    <xsl:if test="$vpocet!=0">
      <li>vektorové vrstvy (<xsl:value-of select="$vpocet"/>):
      <ul>
	<!--
	    <xsl:for-each select="/dataset/vektor/vrstva">
	    <xsl:sort select="." order="ascending" lang="cs"/>
	    <li><xsl:value-of select="@id"/></li>
	    </xsl:for-each>
	-->
	<xsl:apply-templates select="vektor/vrstva" mode="seznam">
	  <xsl:sort select="@id" order="ascending"/>
	</xsl:apply-templates>
      </ul>
      </li>
    </xsl:if>
  </ul>
</xsl:template>

<xsl:template match="dataset/mapset" mode="uplne">
  <h2><xsl:value-of select="@id"/>:</h2>
  <xsl:variable name="rpocet" select="count(rastr//vrstva)"/>
  <xsl:if test="$rpocet!=0">
    <h3>Rastrové vrstvy:</h3>
    <xsl:apply-templates select="rastr/vrstva" mode="uplne">
      <xsl:sort select="@id" order="ascending"/>
    </xsl:apply-templates>
  </xsl:if>
  <xsl:variable name="vpocet" select="count(vektor//vrstva)"/>
  <xsl:if test="$vpocet!=0">
    <h3>Vektorové vrstvy:</h3>
    <xsl:apply-templates select="vektor/vrstva" mode="uplne">      
      <xsl:sort select="@id" order="ascending"/>
    </xsl:apply-templates>
  </xsl:if>
  <hr />
</xsl:template>

<xsl:template match="dataset/mapset" mode="verze">
  <tr>
    <td>Mapset <b><xsl:value-of select="@id"/></b></td>
    <td>:</td>
    <td>verze</td>
    <td><xsl:value-of select="@verze"/></td>
    <td>/</td>
    <td><xsl:value-of select="@datum"/></td>
  </tr>
</xsl:template>

</xsl:stylesheet>