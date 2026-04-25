-- ruby-filter.lua
-- Pandoc Lua filter: converts HTML <ruby>X<rt>Y</rt></ruby> to LaTeX \ruby{X}{Y}
-- for PDF output via XeLaTeX/LuaLaTeX with luatexja-ruby or pxrubrica.

function RawInline(el)
  if el.format == "html" then
    -- Match <ruby>BASE<rt>READING</rt></ruby>
    local base, reading = el.text:match("<ruby>(.-)<rt>(.-)</rt></ruby>")
    if base and reading then
      if FORMAT:match("latex") then
        return pandoc.RawInline("latex", "\\ruby{" .. base .. "}{" .. reading .. "}")
      else
        return el
      end
    end
  end
end

function Meta(meta)
  if FORMAT:match("latex") then
    local includes = meta["header-includes"]
    if not includes then
      includes = pandoc.MetaList({})
    end
    table.insert(includes, pandoc.MetaBlocks({
      pandoc.RawBlock("latex", "\\usepackage{luatexja-ruby}")
    }))
    meta["header-includes"] = includes
    return meta
  end
end
