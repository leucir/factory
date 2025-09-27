# Factory Storage

This repository is a prototype. The ideas below are evolving; they are intended to guide experimentation and can be adapted as we learn.

The layered image prototype keeps binary/blobby artifacts separate from the module code. This directory simulates an external object store.

## Structure

```
storage/
├── objectstore/             # Placeholder for remote assets (e.g., models)
│   └── models/              # Model weights staged for builds/tests
└── README.md
```

Use this area to stash large assets that the build pipeline can mount or copy as part of the app layer. Module fragments reference the object store via scripts or environment variables when needed.
