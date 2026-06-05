# CHARUTEI — App Mobile (Expo)

Cliente do BFF. Fluxo: **login → captura de anilha → reconhecimento → adicionar à coleção**.
A inteligência vive no backend (cascata cost-aware); o app só chama a API.

## Rodar
```bash
# 1. Suba o BFF (na raiz do repo)
uv run --extra serve uvicorn charutei_api.main:app --port 8000

# 2. Instale e rode o app
cd apps/mobile
npm install
npx expo start           # abra no Expo Go (iOS/Android) ou simulador
```

Configure a URL da API em `app.json` (`extra.apiBaseUrl`). No simulador iOS use
`http://localhost:8000`; em device físico use o IP da sua máquina.

## Notas (MVP)
- **Câmera**: usa `expo-camera` (roda no Expo Go). Em produção, trocar por **react-native-vision-camera**
  (captura de alta qualidade) conforme o blueprint — exige dev build.
- **Texto da anilha**: no MVP o pipeline de visão é determinístico/fake; a tela inclui um campo de texto
  que simula o que o modelo multimodal/OCR leria. Em produção, só a imagem é enviada.
- **Auth**: token livre em dev (FakeAuthProvider no BFF). Em produção, Supabase Auth (JWT).
- **Status**: este app é entregue como código; **não foi executado em simulador** neste ambiente.
