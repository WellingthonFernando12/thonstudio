# Wellingthon Fernando | Link in Bio

Landing page premium estilo Link in Bio para converter visitantes do Instagram em conversas no WhatsApp.

## Manutencao

Edite `index.html` para trocar textos, foto e links.
Edite `styles.css` para alterar cores, espacamentos e animacoes.

Para adicionar a foto depois, substitua o bloco `.avatar` no `index.html` por uma imagem:

```html
<img class="avatar-image" src="./foto.jpg" alt="Wellingthon Fernando" />
```

## Deploy sugerido

Vercel:

```bash
npx vercel --prod
```

Cloudflare Pages:

```bash
npx wrangler pages deploy . --project-name wellingthon-link-in-bio
```
